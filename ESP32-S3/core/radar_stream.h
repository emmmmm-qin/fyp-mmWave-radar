#pragma once
#include "ti_mpd_packet.h"

namespace fyp::radar {
using Frame = ti_mpd::Frame;
using Sink = void (*)(const Frame&, std::uint64_t);
// Single producer. Call feed(nullptr, 0, ...) during silence to expire candidates.
class Stream {
public:
    static constexpr std::size_t capacity = 8192;
    void reset() { used_ = 0; }
    void feed(const std::uint8_t* bytes, std::size_t n, std::uint64_t now, Sink sink);
private:
    void scan(std::uint64_t now, Sink sink, bool expired);
    std::array<std::uint8_t, capacity> buf_{};
    std::size_t used_ = 0;
    std::uint64_t start_ = 0, last_ = 0;
};

class Heartbeat {
public:
    void valid(std::uint64_t now) { next_ = now + 2000; }
    bool due(std::uint64_t now) {
        if (now < next_) return false;
        next_ = now + 1000;
        return true;
    }
private:
    std::uint64_t next_ = 0;
};

// Pass nullptr for an unavailable heartbeat. Returns length including LF or 0 on error.
inline constexpr std::size_t line_capacity = 6144;
enum class Source { Radar, Demo };
std::size_t encode(char* out, std::size_t capacity, const Frame* frame, std::uint64_t now,
                   Source source = Source::Radar);
} // namespace fyp::radar
