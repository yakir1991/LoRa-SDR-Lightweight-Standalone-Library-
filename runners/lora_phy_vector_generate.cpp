#include <lora_phy/phy.hpp>
#include <lora_phy/LoRaCodes.hpp>

#include <complex>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <cmath>
#include <random>
#include <set>
#include <string>
#include <vector>
#include <dirent.h>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <array>

using namespace lora_phy;

namespace {

void usage(const char* prog) {
    std::cerr << "Usage: " << prog
              << " --out=DIR [--sf=N] [--bytes=N] [--seed=N] [--osr=N]"
              << " [--bw=HZ] [--window=hann] [--cfo-bins=X] [--time-offset=N]\n";
}

// base64 encoding
std::string base64_encode(const std::vector<uint8_t>& data) {
    static const char tbl[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    size_t i = 0;
    while (i + 2 < data.size()) {
        uint32_t b = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2];
        out.push_back(tbl[(b >> 18) & 0x3f]);
        out.push_back(tbl[(b >> 12) & 0x3f]);
        out.push_back(tbl[(b >> 6) & 0x3f]);
        out.push_back(tbl[b & 0x3f]);
        i += 3;
    }
    if (i + 1 == data.size()) {
        uint32_t b = data[i] << 16;
        out.push_back(tbl[(b >> 18) & 0x3f]);
        out.push_back(tbl[(b >> 12) & 0x3f]);
        out.push_back('=');
        out.push_back('=');
    } else if (i + 2 == data.size()) {
        uint32_t b = (data[i] << 16) | (data[i + 1] << 8);
        out.push_back(tbl[(b >> 18) & 0x3f]);
        out.push_back(tbl[(b >> 12) & 0x3f]);
        out.push_back(tbl[(b >> 6) & 0x3f]);
        out.push_back('=');
    }
    // Insert line breaks every 76 characters to match Python's base64.encode
    std::string wrapped;
    for (size_t j = 0; j < out.size(); j += 76) {
        size_t len = std::min<size_t>(76, out.size() - j);
        wrapped.append(out.substr(j, len));
        wrapped.push_back('\n');
    }
    return wrapped;
}

std::string run_sha256(const std::string& p) {
    std::array<char, 256> buf{};
    std::string cmd = "sha256sum " + p;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
    if (!pipe) return {};
    if (fgets(buf.data(), buf.size(), pipe.get()) == nullptr) return {};
    std::string hash(buf.data());
    return hash.substr(0, hash.find_first_of(" \t"));
}

void b64_and_remove(const std::string& in, std::string& out, std::string& sha) {
    std::ifstream f(in, std::ios::binary);
    std::vector<uint8_t> data((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    f.close();
    std::string b64 = base64_encode(data);
    out = in + ".b64";
    std::ofstream g(out, std::ios::binary);
    g.write(b64.data(), b64.size());
    g.close();
    std::remove(in.c_str());
    sha = run_sha256(out);
}

void apply_offsets(const std::string& iq_file, float cfo_bins, float time_offset, unsigned sf, unsigned osr) {
    if (cfo_bins == 0.0f && time_offset == 0.0f) return;
    std::ifstream f(iq_file);
    std::vector<std::complex<double>> samples;
    std::string line;
    while (std::getline(f, line)) {
        auto comma = line.find(',');
        if (comma == std::string::npos) continue;
        double re = std::stod(line.substr(0, comma));
        double im = std::stod(line.substr(comma + 1));
        samples.emplace_back(re, im);
    }
    f.close();
    size_t N = (size_t(1) << sf) * osr;
    if (cfo_bins != 0.0f) {
        for (size_t n = 0; n < samples.size(); ++n) {
            double ph = 2.0 * M_PI * cfo_bins * (n % N) / N;
            std::complex<double> rot(std::cos(ph), std::sin(ph));
            samples[n] *= rot;
        }
    }
    if (time_offset != 0.0f) {
        int shift = static_cast<int>(std::round(time_offset));
        if (shift > 0) {
            samples.erase(samples.begin(), samples.begin() + std::min<size_t>(shift, samples.size()));
            samples.insert(samples.end(), shift, std::complex<double>(0,0));
        } else if (shift < 0) {
            shift = -shift;
            samples.insert(samples.begin(), shift, std::complex<double>(0,0));
            if (samples.size() > shift)
                samples.resize(samples.size());
        }
    }
    std::string out = iq_file.substr(0, iq_file.find_last_of('/')) + "/iq_samples_offset.csv";
    std::ofstream g(out);
    for (auto& s : samples) g << s.real() << "," << s.imag() << "\n";
}

} // namespace

int main(int argc, char** argv) {
    unsigned sf = 7;
    unsigned seed = 1;
    unsigned osr = 1;
    bandwidth bw = bandwidth::bw_125;
    size_t byte_count = 16;
    std::string out_subdir;
    window_type win = window_type::window_none;
    float cfo_bins = 0.0f;
    float time_offset = 0.0f;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg.rfind("--sf=", 0) == 0) {
            sf = static_cast<unsigned>(std::stoul(arg.substr(5)));
        } else if (arg.rfind("--seed=", 0) == 0) {
            seed = static_cast<unsigned>(std::stoul(arg.substr(7)));
        } else if (arg.rfind("--bytes=", 0) == 0) {
            byte_count = static_cast<size_t>(std::stoul(arg.substr(8)));
        } else if (arg.rfind("--osr=", 0) == 0) {
            osr = static_cast<unsigned>(std::stoul(arg.substr(6)));
        } else if (arg.rfind("--bw=", 0) == 0) {
            unsigned val = static_cast<unsigned>(std::stoul(arg.substr(5)));
            if (val == 125000)
                bw = bandwidth::bw_125;
            else if (val == 250000)
                bw = bandwidth::bw_250;
            else if (val == 500000)
                bw = bandwidth::bw_500;
            else {
                std::cerr << "Unsupported bandwidth\n";
                return 1;
            }
        } else if (arg.rfind("--out=", 0) == 0) {
            out_subdir = arg.substr(6);
        } else if (arg.rfind("--window=",0)==0) {
            std::string w = arg.substr(9);
            if (w == "hann") win = window_type::window_hann; else win = window_type::window_none;
        } else if (arg.rfind("--cfo-bins=",0)==0) {
            cfo_bins = std::stof(arg.substr(11));
        } else if (arg.rfind("--time-offset=",0)==0) {
            time_offset = std::stof(arg.substr(14));
        } else {
            usage(argv[0]);
            return 1;
        }
    }
    if (out_subdir.empty()) {
        usage(argv[0]);
        return 1;
    }
    std::string out_dir = std::string("vectors/lora_phy/") + out_subdir;
    std::string mkcmd = std::string("mkdir -p ") + out_dir;
    std::system(mkcmd.c_str());

    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> dist(0,255);
    std::vector<uint8_t> payload(byte_count);
    for (size_t i=0;i<byte_count;++i) payload[i]=static_cast<uint8_t>(dist(rng));

    const size_t nibble_count = byte_count * 2;
    const size_t cw_count = ((nibble_count + sf - 1) / sf) * sf;
    const size_t rdd = 4;
    const size_t blocks = cw_count / sf;
    const size_t symbol_count = blocks * (4 + rdd);
    const size_t N = size_t(1) << sf;

    std::vector<uint8_t> pre_interleave(cw_count,0);
    for (size_t i=0;i<nibble_count;++i){
        uint8_t b = payload[i/2];
        uint8_t nib = (i&1)?(b&0x0f):(b>>4);
        pre_interleave[i] = encodeHamming84sx(nib);
    }

    std::vector<uint16_t> post_interleave(symbol_count);
    std::vector<uint16_t> demod(symbol_count);
    std::vector<uint8_t> deinterleave(cw_count,0);
    std::vector<uint8_t> decoded(byte_count);
    std::vector<std::complex<float>> fft_in(N), fft_out(N*osr);
    std::vector<float> window(N);
    std::vector<std::complex<float>> samples((symbol_count+2)*N*osr);

    lora_workspace ws{}; ws.symbol_buf=post_interleave.data(); ws.fft_in=fft_in.data(); ws.fft_out=fft_out.data(); ws.window=window.data();
    lora_params params{}; params.sf=sf; params.bw=bw; params.cr=0; params.osr=osr; params.window=win;
    if (init(&ws,&params)!=0){ std::cerr<<"init failed\n"; return 1; }

    ssize_t produced = encode(&ws,payload.data(),payload.size(),post_interleave.data(),post_interleave.size());
    if (produced<0){ std::cerr<<"encode failed\n"; return 1; }

    ssize_t sample_count = modulate(&ws,post_interleave.data(),produced,samples.data(),samples.size());
    if (sample_count<0){ std::cerr<<"modulate failed\n"; return 1; }

    ssize_t demod_syms = demodulate(&ws,samples.data(),sample_count,demod.data(),demod.size());
    if (demod_syms<0){ std::cerr<<"demodulate failed\n"; return 1; }

    diagonalDeterleaveSx(demod.data(),symbol_count,deinterleave.data(),sf,rdd);

    for(size_t i=0;i<byte_count;++i){
        bool err=false,bad=false; uint8_t hi=decodeHamming84sx(deinterleave[2*i],err,bad)&0x0f; err=bad=false; uint8_t lo=decodeHamming84sx(deinterleave[2*i+1],err,bad)&0x0f; decoded[i]=static_cast<uint8_t>((hi<<4)|lo);
    }

    // write files
    std::ofstream f;
    f.open(out_dir+"/payload.bin",std::ios::binary); f.write((char*)payload.data(),payload.size()); f.close();
    f.open(out_dir+"/pre_interleave.csv"); for(size_t i=0;i<cw_count;++i) f<<unsigned(pre_interleave[i])<<"\n"; f.close();
    f.open(out_dir+"/post_interleave.csv"); for(size_t i=0;i<symbol_count;++i) f<<post_interleave[i]<<"\n"; f.close();
    f.open(out_dir+"/iq_samples.csv"); for(ssize_t i=0;i<sample_count;++i) f<<samples[i].real()<<","<<samples[i].imag()<<"\n"; f.close();
    f.open(out_dir+"/demod_symbols.csv"); for(size_t i=0;i<symbol_count;++i) f<<demod[i]<<"\n"; f.close();
    f.open(out_dir+"/deinterleave.csv"); for(size_t i=0;i<cw_count;++i) f<<unsigned(deinterleave[i])<<"\n"; f.close();
    f.open(out_dir+"/decoded.bin",std::ios::binary); f.write((char*)decoded.data(),decoded.size()); f.close();

    apply_offsets(out_dir+"/iq_samples.csv",cfo_bins,time_offset,sf,osr);

    struct Record { std::string name; std::string sha; };
    std::vector<Record> records;
    DIR* dir = opendir(out_dir.c_str());
    struct dirent* ent;
    while ((ent = readdir(dir)) != nullptr) {
        std::string name = ent->d_name;
        if (name == "." || name == ".." || name == "manifest.json") continue;
        std::string path = out_dir + "/" + name;
        std::string b64name, sha; b64_and_remove(path, b64name, sha);
        size_t pos = b64name.find_last_of('/');
        std::string fname = b64name.substr(pos+1);
        records.push_back(Record{fname, sha});
    }
    closedir(dir);

    // write manifest
    std::ofstream m(out_dir+"/manifest.json");
    m << "{\n";
    m << "  \"sf\": "<<sf<<",\n";
    m << "  \"seed\": "<<seed<<",\n";
    m << "  \"bytes\": "<<byte_count<<",\n";
    m << "  \"osr\": "<<osr<<",\n";
    m << "  \"bw\": "<< (bw==bandwidth::bw_125?125000:(bw==bandwidth::bw_250?250000:500000)) <<",\n";
    m << "  \"files\": [\n";
    for (size_t i=0;i<records.size();++i){
        m << "    {\"name\": \""<<records[i].name<<"\", \"sha256\": \""<<records[i].sha<<"\"}";
        if (i+1<records.size()) m << ",";
        m << "\n";
    }
    m << "  ]\n";
    m << "}\n";
    m.close();

    return 0;
}
