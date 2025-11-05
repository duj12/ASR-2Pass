#include <wfst-decoder.h>
namespace funasr {
WfstDecoder::WfstDecoder(fst::Fst<fst::StdArc>* lm,
                         PhoneSet* phone_set, Vocab* vocab,
                         float glob_beam, float lat_beam, float am_scale)
:dec_opts_(glob_beam, lat_beam, am_scale), decodable_(dec_opts_.acoustic_scale),
 lm_(lm), phone_set_(phone_set), vocab_(vocab) {
  decoder_ = std::shared_ptr<kaldi::LatticeFasterOnlineDecoder>(
             new kaldi::LatticeFasterOnlineDecoder(*lm_, dec_opts_));
}

WfstDecoder::~WfstDecoder() {
}

void WfstDecoder::StartUtterance() {
  if (decoder_) {
    cur_frame_ = 0;
    cur_token_ = 0;
    decodable_.Reset();
    decoder_->InitDecoding();
  }
}

void WfstDecoder::EndUtterance() {
}

string WfstDecoder::Search(float *in, int len, int64_t token_num) {
  string result;
  if (len == 0) {
    return "";
  }
  std::vector<std::vector<float>> logp_vec;
  int blk_phn_id = phone_set_->GetBlkPhnId();
  for (int i = 0; i < len - 1; i++) {
    std::vector<float> tmp_logp;
    for (int j = 0; j < token_num; j++) {
      tmp_logp.push_back((in + i * token_num)[j]);
    }
    logp_vec.push_back(tmp_logp);
  }
  for (int i = 0; i < logp_vec.size(); i++) {
    cur_frame_++;
    decodable_.AcceptLoglikes(logp_vec[i]);
    decoder_->AdvanceDecoding(&decodable_, 1);
    cur_token_++;
  }
  if (cur_token_ > 0) {
    std::vector<int> words;
    kaldi::Lattice lattice;
    decoder_->GetBestPath(&lattice, false);
    std::vector<int> alignment;
    kaldi::LatticeWeight weight;
    fst::GetLinearSymbolSequence(lattice, &alignment, &words, &weight);
    result = vocab_->Vector2StringV2(words);
  }
  return result;
}

string WfstDecoder::FinalizeDecode(bool is_stamp, std::vector<float> us_alphas, std::vector<float> us_cif_peak) {
  string result;
  if (cur_token_ > 0) {
    std::vector<int> words;
    kaldi::Lattice lattice;
    decodable_.SetFinished();
    decoder_->FinalizeDecoding();
    decoder_->GetBestPath(&lattice, true);
    std::vector<int> alignment;
    kaldi::LatticeWeight weight;
    fst::GetLinearSymbolSequence(lattice, &alignment, &words, &weight);
    
    if(!is_stamp){
        return vocab_->Vector2StringV2(words);
    }else{
        std::vector<std::string> char_list;
        std::vector<std::vector<float>> timestamp_list;
        std::string res_str;
        vocab_->Vector2String(words, char_list);
        // split chinese word to char
        std::vector<std::string> split_chars;
        for(auto& word:char_list){
          std::vector<std::string> word2char;
          SplitChiEngCharacters(word, word2char);
          split_chars.insert(split_chars.end(), word2char.begin(), word2char.end());
        }
        // std::vector<string> raw_char(char_list);
        TimestampOnnx(us_alphas, us_cif_peak, split_chars, res_str, timestamp_list);

        return PostProcess(split_chars, timestamp_list);
    }
  }
  return result;
}


string WfstDecoder::CtcSearch(std::vector<std::vector<float>> logp_vec) {
  if (logp_vec.size() < 1){
    return "";
  }
  int blk_phn_id = phone_set_->GetBlkPhnId();
  
  std::vector<int> greedy_token;
  // Step through each frame
  for (int i = 0; i < logp_vec.size(); i++) {
    //float blank_score = std::exp(logp_vec[i][blk_phn_id]);
    float blank_score = 0.0;   // ctc_output_logit is not strictly log-softmax prob
    if (blank_score > blank_skip_thresh) {
      // 跳过高概率blank帧
      is_last_frame_blank_ = true;
      last_frame_prob_ = logp_vec[i];
    } else {
      // 当前帧的最佳token
      int cur_best = std::max_element(logp_vec[i].begin(), logp_vec[i].end()) - logp_vec[i].begin();
      greedy_token.push_back(cur_best);
      // 如果上一个是blank且当前和上一次相同token，则补一帧blank
      if (cur_best != blk_phn_id && is_last_frame_blank_ && cur_best == last_best_) {
        decodable_.AcceptLoglikes(last_frame_prob_);
        decoder_->AdvanceDecoding(&decodable_, 1);
        decoded_frames_mapping_.push_back(num_frames_ - 1);
      }

      last_best_ = cur_best;
      cur_frame_++;
      decodable_.AcceptLoglikes(logp_vec[i]);
      decoder_->AdvanceDecoding(&decodable_, 1);
      cur_token_++;
      decoded_frames_mapping_.push_back(num_frames_);
      is_last_frame_blank_ = false;
    }
    num_frames_++;
  }

  // 输出最优路径
  std::string result;
  if (!decoded_frames_mapping_.empty()) {
    kaldi::Lattice lat;
    decoder_->GetBestPath(&lat, false);
    std::vector<int> alignment, words;
    kaldi::LatticeWeight weight;
    fst::GetLinearSymbolSequence(lat, &alignment, &words, &weight);

    std::vector<int> inputs, times;
    ConvertToInputs(alignment, &inputs, &times);
    result = vocab_->Vector2StringV2(words);
  }

  return result;
}

string WfstDecoder::CtcFinalizeDecode() {
  decodable_.SetFinished();
  decoder_->FinalizeDecoding();

  std::string result;
  if (decoded_frames_mapping_.empty()) {
    return result;
  }

  std::vector<kaldi::Lattice> nbest_lats;
  int nbest = 1;
  if (nbest == 1) {
    kaldi::Lattice lat;
    decoder_->GetBestPath(&lat, true);
    nbest_lats.push_back(std::move(lat));
  } else {
    kaldi::CompactLattice clat;
    decoder_->GetLattice(&clat, true);
    kaldi::Lattice lat, nbest_lat;
    fst::ConvertLattice(clat, &lat);
    fst::ShortestPath(lat, &nbest_lat, nbest);
    fst::ConvertNbestToVector(nbest_lat, &nbest_lats);
  }

  std::vector<int> alignment, words;
  kaldi::LatticeWeight weight;
  fst::GetLinearSymbolSequence(nbest_lats[0], &alignment, &words, &weight);
  ConvertToInputs(alignment, &alignment);

  result = vocab_->Vector2StringV2(words);
  return result;
}

void WfstDecoder::ConvertToInputs(const std::vector<int>& alignment,
                                  std::vector<int>* input,
                                  std::vector<int>* time) {
  input->clear();
  if (time != nullptr) time->clear();

  int blk_phn_id = phone_set_->GetBlkPhnId();

  for (size_t cur = 0; cur < alignment.size(); ++cur) {
    int sym = alignment[cur];
    // 忽略 blank
    if (sym == blk_phn_id) continue;
    // 跳过重复标签
    if (cur > 0 && alignment[cur] == alignment[cur - 1]) continue;

    input->push_back(sym);
    if (time != nullptr && cur < decoded_frames_mapping_.size()) {
      time->push_back(decoded_frames_mapping_[cur]);
    }
  }
}

void WfstDecoder::LoadHwsRes(int inc_bias, unordered_map<string, int> &hws_map) {
  try {
    if (!hws_map.empty()) {
      bias_lm_ = std::make_shared<BiasLm>(hws_map, inc_bias,
                                          *phone_set_, *vocab_);
      decoder_->SetBiasLm(bias_lm_);
    }
  } catch (std::exception const &e) {
        LOG(ERROR) << "Error when load wfst hotwords resource: " << e.what();
        exit(0);
  }
}

void WfstDecoder::UnloadHwsRes() {
  if (bias_lm_) {
    decoder_->ClearBiasLm();
    bias_lm_.reset();
  }
}

} // namespace funasr
