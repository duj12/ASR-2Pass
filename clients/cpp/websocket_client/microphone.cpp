/**
 * Copyright FunASR (https://github.com/alibaba-damo-academy/FunASR). All Rights
 * Reserved. MIT License  (https://opensource.org/licenses/MIT)
 */

#include "microphone.h"

#include <stdio.h>
#include <stdlib.h>

#include "portaudio.h"  // NOLINT
using namespace std;

Microphone::Microphone() {
  PaError err = Pa_Initialize();
  if (err != paNoError) {
    std::cout <<"portaudio error: " << Pa_GetErrorText(err) << endl;
    exit(-1);
  }
}

Microphone::~Microphone() {
  PaError err = Pa_Terminate();
  if (err != paNoError) {
    std::cout <<"portaudio error: " << Pa_GetErrorText(err) << endl;
    exit(-1);
  }
}
