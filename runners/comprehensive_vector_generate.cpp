#include <lora_phy/LoRaCodes.hpp>

#include <complex>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>
#include <cstdlib>

using namespace std;

struct LoRaConfig {
    int sf;
    int bw;
    int cr;
    bool explicit_header;
    bool crc_enabled;
    bool whitening_enabled;
    bool interleaving_enabled;
    string name;
};

vector<LoRaConfig> getTestConfigs() {
    return {
        {7,125,1,true,true,true,true,"SF7_125k_CR45"},
        {7,125,4,true,true,true,true,"SF7_125k_CR48"},
        {9,125,1,true,true,true,true,"SF9_125k_CR45"},
        {9,125,4,true,true,true,true,"SF9_125k_CR48"},
        {12,125,1,true,true,true,true,"SF12_125k_CR45"},
        {12,125,4,true,true,true,true,"SF12_125k_CR48"}
    };
}

vector<vector<uint8_t>> getTestPayloads(){
    return {
        {0x48,0x65,0x6C,0x6C,0x6F},
        {0x57,0x6F,0x72,0x6C,0x64},
        {0x54,0x65,0x73,0x74},
        {0x4C,0x6F,0x52,0x61},
        {0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08}
    };
}

vector<complex<double>> generateChirp(int N, bool up){
    vector<complex<double>> chirp(N);
    for(int i=0;i<N;i++){
        double phase = 2.0*M_PI*i*i/(2.0*N);
        if(!up) phase=-phase;
        chirp[i]=complex<double>(cos(phase),sin(phase));
    }
    return chirp;
}

vector<complex<double>> generateLoRaModulation(const vector<uint8_t>& payload,const LoRaConfig& config){
    int N = 1<<config.sf;
    vector<complex<double>> iq_samples;
    for(int i=0;i<10;i++){ auto c=generateChirp(N,true); iq_samples.insert(iq_samples.end(),c.begin(),c.end()); }
    for(int i=0;i<2;i++){ auto c=generateChirp(N,false); iq_samples.insert(iq_samples.end(),c.begin(),c.end()); }
    vector<int> bits; for(uint8_t b:payload){ for(int i=7;i>=0;i--) bits.push_back((b>>i)&1); }
    for(size_t i=0;i<bits.size(); i+=config.sf){
        int symbol=0; for(int j=0;j<config.sf && i+j<bits.size(); j++) symbol|=bits[i+j]<<(config.sf-1-j);
        double phase = 2.0*M_PI*symbol/N; auto chirp=generateChirp(N,true);
        for(int k=0;k<N;k++){ chirp[k]*=complex<double>(cos(phase*k),sin(phase*k)); }
        iq_samples.insert(iq_samples.end(),chirp.begin(),chirp.end());
    }
    return iq_samples;
}

void generateHammingVectors(const string& dir){
    ofstream h(dir+"/hamming_tests.bin", ios::binary);
    uint32_t count=0; h.write((char*)&count,sizeof(count));
    for(int i=0;i<16;i++){
        uint8_t data=i; uint8_t enc=encodeHamming84sx(data); bool err=false,bad=false; uint8_t dec=decodeHamming84sx(enc,err,bad);
        uint8_t type=0; h.write((char*)&type,1); h.write((char*)&data,1); h.write((char*)&enc,1); h.write((char*)&dec,1); h.write((char*)&err,1); h.write((char*)&bad,1); count++;
    }
    h.seekp(0); h.write((char*)&count,sizeof(count)); h.close();
}

void generateModulationVectors(const string& dir){
    ofstream mod(dir+"/modulation_tests.bin", ios::binary);
    uint32_t count=0; mod.write((char*)&count,sizeof(count));
    auto cfgs=getTestConfigs(); auto payloads=getTestPayloads();
    for(auto& cfg:cfgs){
        for(auto& p:payloads){
            auto iq=generateLoRaModulation(p,cfg); uint8_t type=0; mod.write((char*)&type,1);
            mod.write((char*)&cfg.sf,sizeof(cfg.sf)); mod.write((char*)&cfg.bw,sizeof(cfg.bw)); mod.write((char*)&cfg.cr,sizeof(cfg.cr));
            uint32_t ps=p.size(); mod.write((char*)&ps,sizeof(ps)); mod.write((char*)p.data(),p.size());
            uint32_t iqsize=iq.size(); mod.write((char*)&iqsize,sizeof(iqsize)); mod.write((char*)iq.data(),iq.size()*sizeof(complex<double>)); count++;
        }
    }
    mod.seekp(0); mod.write((char*)&count,sizeof(count)); mod.close();
}

int main(int argc,char** argv){
    string out="vectors/lora_sdr_reference_cpp";
    for(int i=1;i<argc;i++){ string arg=argv[i]; if(arg.rfind("--out=",0)==0) out=arg.substr(6); }
    string mkcmd = string("mkdir -p ") + out;
    std::system(mkcmd.c_str());
    generateHammingVectors(out);
    generateModulationVectors(out);
    std::cout << "Generated vectors under " << out << std::endl;
    return 0;
}
