cmake_minimum_required(VERSION 3.16)

project(FunASRWebscoket) 

set(CMAKE_CXX_STANDARD 14 CACHE STRING "The C++ version to be used.")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

option(ENABLE_WEBSOCKET "Whether to build websocket server" ON)
option(ENABLE_PORTAUDIO "Whether to build portaudio server" ON)
 
if(ENABLE_WEBSOCKET)
  # cmake_policy(SET CMP0135 NEW)
  include(FetchContent)
  FetchContent_Declare(websocketpp
  GIT_REPOSITORY https://github.com/zaphoyd/websocketpp.git
    GIT_TAG 0.8.2
    SOURCE_DIR ${PROJECT_SOURCE_DIR}/third_party/websocket
    )
  
  FetchContent_MakeAvailable(websocketpp)
  include_directories(${PROJECT_SOURCE_DIR}/third_party/websocket)
   
  FetchContent_Declare(asio
     URL   https://github.com/chriskohlhoff/asio/archive/refs/tags/asio-1-24-0.tar.gz
   SOURCE_DIR ${PROJECT_SOURCE_DIR}/third_party/asio
  )
  
  FetchContent_MakeAvailable(asio)
  include_directories(${PROJECT_SOURCE_DIR}/third_party/asio/asio/include)
 
  FetchContent_Declare(json
     URL   https://github.com/nlohmann/json/archive/refs/tags/v3.11.2.tar.gz
   SOURCE_DIR ${PROJECT_SOURCE_DIR}/third_party/json
  )
  
  FetchContent_MakeAvailable(json)
  include_directories(${PROJECT_SOURCE_DIR}/third_party/json/include)

endif()

if(ENABLE_PORTAUDIO)
  include(FetchContent)

  set(portaudio_URL  "http://files.portaudio.com/archives/pa_stable_v190700_20210406.tgz")
  set(portaudio_URL2 "https://isv-data.oss-cn-hangzhou.aliyuncs.com/ics/MaaS/ASR/dep_libs/pa_stable_v190700_20210406.tgz")
  set(portaudio_HASH "SHA256=47efbf42c77c19a05d22e627d42873e991ec0c1357219c0d74ce6a2948cb2def")

  FetchContent_Declare(portaudio
    URL
      ${portaudio_URL}
      ${portaudio_URL2}
    URL_HASH          ${portaudio_HASH}
    SOURCE_DIR ${PROJECT_SOURCE_DIR}/third_party/portaudio
  )

  FetchContent_MakeAvailable(portaudio)
  include_directories(${PROJECT_SOURCE_DIR}/third_party/portaudio/include)

endif()

include_directories(${CMAKE_SOURCE_DIR}/include)

# install openssl first apt-get install libssl-dev
find_package(OpenSSL REQUIRED)
if(APPLE)
    set(OPENSSL_ROOT_DIR $ENV{OPENSSL_ROOT_DIR})
    include_directories(${OPENSSL_INCLUDE_DIR})
    link_directories(${OPENSSL_ROOT_DIR}/lib)
endif()

if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64")
    add_compile_options(-arch arm64)
endif()

add_executable(funasr-wss-client "funasr-wss-client.cpp" "audio.cpp" "resample.cpp")
add_executable(funasr-wss-client-2pass "funasr-wss-client-2pass.cpp" "audio.cpp" "resample.cpp" "microphone.cpp")
target_link_libraries(funasr-wss-client PUBLIC ssl crypto pthread)
target_link_libraries(funasr-wss-client-2pass PUBLIC ssl crypto pthread portaudio)
