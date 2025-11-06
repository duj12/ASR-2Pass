#ifndef DECODER_BASE_H_
#define DECODER_BASE_H_

#include <string>
#include <vector>
#include <unordered_map>

namespace funasr {

class Decoder {
public:
    virtual ~Decoder() = default;
    
    virtual void StartUtterance() {};
    virtual void EndUtterance() {};

    // 适配 CIF WFST Beam Search, Paraformer model
    virtual std::string Search(float* in, int len, int64_t token_nums) { return ""; }
    virtual std::string FinalizeDecode(bool is_stamp=false, 
                                       std::vector<float> us_alphas={}, 
                                       std::vector<float> us_cif_peak={}) { return ""; }
    
    // 对于 CTC WFST Beam Search/ Prefix Beam Search, SenseVoice model，可重载如下两个接口
    virtual std::string CtcSearch(std::vector<std::vector<float>> ctc_logp) { return ""; }
    virtual std::string CtcFinalizeDecode() { return ""; }

    // 热词增强接口
    virtual void LoadHwsRes(int inc_bias, std::unordered_map<std::string, int>& hws_map) {}
    virtual void UnloadHwsRes() {}
};

}  // namespace funasr

#endif  // DECODER_BASE_H_
