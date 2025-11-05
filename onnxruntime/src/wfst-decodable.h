/**
 * @file wfst_decodable.h
 * @brief Interface for models that support WFST decoding (e.g., Paraformer, SenseVoiceSmall)
 */

#pragma once

#include <memory>
#include <vector>
#include <string>
#include "fst/fstlib.h"
#include "vocab.h"
#include "phone-set.h"

namespace funasr {

class WfstDecodable {
public:
    std::shared_ptr<fst::Fst<fst::StdArc>> lm_;
    PhoneSet* phone_set_;
    Vocab* lm_vocab;

    virtual ~WfstDecodable() = default;
    virtual std::shared_ptr<fst::Fst<fst::StdArc>> GetLm() const = 0;
    virtual PhoneSet* GetPhoneSet() const = 0;
    virtual Vocab* GetLmVocab() const = 0;
};

}  // namespace funasr
