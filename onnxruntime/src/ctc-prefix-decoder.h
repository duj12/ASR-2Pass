// Copyright (c) 2020 Mobvoi Inc (Binbin Zhang)
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.


#ifndef DECODER_CTC_PREFIX_BEAM_SEARCH_H_
#define DECODER_CTC_PREFIX_BEAM_SEARCH_H_

#include <memory>
#include <unordered_map>
#include <utility>
#include <vector>
#include "decoder.h"
#include "vocab.h"
#include "phone-set.h"
#include "context_graph.h"
#include "util.h"

namespace funasr {

inline float LogAdd(float x, float y) {
  static float num_min = -std::numeric_limits<float>::max();
  if (x <= num_min) return y;
  if (y <= num_min) return x;
  float xmax = std::max(x, y);
  return std::log(std::exp(x - xmax) + std::exp(y - xmax)) + xmax;
}

struct WordPiece {
  std::string word;
  int start = -1;
  int end = -1;

  WordPiece(std::string word, int start, int end)
      : word(std::move(word)), start(start), end(end) {}
};

struct DecodeResult {
  float score = -kFloatMax;
  std::string sentence;
  std::vector<WordPiece> word_pieces;

  static bool CompareFunc(const DecodeResult& a, const DecodeResult& b) {
    return a.score > b.score;
  }
};

struct CtcPrefixBeamSearchOptions {
  int blank = 0;  // blank id
  int first_beam_size = 10;
  int second_beam_size = 10;
};

struct PrefixScore {
  float s = -kFloatMax;               // blank ending score
  float ns = -kFloatMax;              // none blank ending score
  float v_s = -kFloatMax;             // viterbi blank ending score
  float v_ns = -kFloatMax;            // viterbi none blank ending score
  float cur_token_prob = -kFloatMax;  // prob of current token
  std::vector<int> times_s;           // times of viterbi blank path
  std::vector<int> times_ns;          // times of viterbi none blank path

  float score() const { return LogAdd(s, ns); }
  float viterbi_score() const { return v_s > v_ns ? v_s : v_ns; }
  const std::vector<int>& times() const {
    return v_s > v_ns ? times_s : times_ns;
  }

  bool has_context = false;
  int context_state = 0;
  float context_score = 0;
  std::vector<int> start_boundaries;
  std::vector<int> end_boundaries;

  void CopyContext(const PrefixScore& prefix_score) {
    context_state = prefix_score.context_state;
    context_score = prefix_score.context_score;
    start_boundaries = prefix_score.start_boundaries;
    end_boundaries = prefix_score.end_boundaries;
  }

  void UpdateContext(const std::shared_ptr<ContextGraph>& context_graph,
                     const PrefixScore& prefix_score, int word_id,
                     int prefix_len) {
    this->CopyContext(prefix_score);

    float score = 0;
    bool is_start_boundary = false;
    bool is_end_boundary = false;

    context_state =
        context_graph->GetNextState(prefix_score.context_state, word_id, &score,
                                    &is_start_boundary, &is_end_boundary);
    context_score += score;
    if (is_start_boundary) start_boundaries.emplace_back(prefix_len);
    if (is_end_boundary) end_boundaries.emplace_back(prefix_len);
  }

  float total_score() const { return score() + context_score; }
};

struct PrefixHash {
  size_t operator()(const std::vector<int>& prefix) const {
    size_t hash_code = 0;
    // here we use KB&DR hash code
    for (int id : prefix) {
      hash_code = id + 31 * hash_code;
    }
    return hash_code;
  }
};

class CtcPrefixDecoder: public Decoder {
 public:
  CtcPrefixDecoder(Vocab* vocab,
    float glob_beam, float lat_beam);
  ~CtcPrefixDecoder();

  void StartUtterance() override;
  void EndUtterance() override;
  std::string CtcSearch(std::vector<std::vector<float>> logp) override; 
  std::string CtcFinalizeDecode() override;
  void Reset();
  void ResetContext(std::shared_ptr<ContextGraph>& context_graph);
  void UpdateOutputs(const std::pair<std::vector<int>, PrefixScore>& prefix);
  void UpdateHypotheses(
      const std::vector<std::pair<std::vector<int>, PrefixScore>>& hpys);
  void UpdateFinalContext();
  void UpdateResult();

  std::shared_ptr<ContextGraph> context_graph_ = nullptr;
  int abs_time_step_ = 0;
  Vocab* vocab_ = nullptr;
  PhoneSet* phone_set_ = nullptr;
  // N-best list and corresponding likelihood_, in sorted order
  std::vector<std::vector<int>> hypotheses_;
  std::vector<float> likelihood_;
  std::vector<float> viterbi_likelihood_;
  std::vector<std::vector<int>> times_;

  std::unordered_map<std::vector<int>, PrefixScore, PrefixHash> cur_hyps_;
  // Outputs contain the hypotheses_ and tags like: <context> and </context>
  std::vector<std::vector<int>> outputs_;
  CtcPrefixBeamSearchOptions opts_;

  std::vector<DecodeResult> result_;

 private:

};



}  // namespace funasr

#endif  // DECODER_CTC_PREFIX_BEAM_SEARCH_H_
