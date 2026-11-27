#include "radar_stream.h"
#include <algorithm>
#include <cinttypes>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace fyp::radar {
namespace {
constexpr std::uint8_t magic[] = {2, 1, 4, 3, 6, 5, 8, 7};
std::uint32_t u32(const std::uint8_t* p) {
    return p[0] | (std::uint32_t(p[1]) << 8) | (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
}
void Stream::scan(std::uint64_t now, Sink sink, bool expired) {
    std::size_t at = 0;
    while (at < used_) {
        const auto* p = buf_.data() + at;
        const auto remaining = used_ - at;
        if (std::memcmp(p, magic, std::min(remaining, sizeof magic)) == 0) {
            if (remaining < 20) {
                if (!expired) break;
            } else {
                const auto size = u32(p + 12);
                if (u32(p + 8) == 0x05050402 && u32(p + 16) == 0xA6432 &&
                    size >= 64 && size <= capacity && size % 32 == 0) {
                    if (size > remaining) {
                        if (!expired) break;
                    } else {
                        const auto decoded = ti_mpd::decode_packet(p, size);
                        if (decoded.status == ti_mpd::DecodeStatus::Ok) {
                            sink(decoded.frame, now);
                            at += size;
                            continue;
                        }
                    }
                }
            }
        }
        ++at; // Search inside a rejected candidate; it may contain the next real header.
    }
    if (at) {
        used_ -= at;
        std::memmove(buf_.data(), buf_.data() + at, used_);
        start_ = now;
    }
}
void Stream::feed(const std::uint8_t* bytes, std::size_t n, std::uint64_t now, Sink sink) {
    if (used_ && (now - last_ >= 250 || now - start_ >= 2000)) scan(now, sink, true);
    while (n) {
        if (!used_) start_ = now;
        const auto take = std::min(n, capacity - used_);
        std::memcpy(buf_.data() + used_, bytes, take);
        used_ += take;
        bytes += take;
        n -= take;
        last_ = now;
        scan(now, sink, false);
    }
}
std::size_t encode(char* out, std::size_t capacity, const Frame* frame, std::uint64_t now, Source source) {
    std::size_t used = 0;
    auto append = [&](const char* fmt, auto... args) {
        int n = std::snprintf(out + used, capacity - used, fmt, args...);
        if (n < 0 || static_cast<std::size_t>(n) >= capacity - used) return false;
        used += n;
        return true;
    };
    const std::size_t count = frame ? std::size_t(frame->major_count) + frame->minor_count : 0;
    if (count > ti_mpd::MAX_POINTS || !append("{\"protocol\":\"fyp-radar\",\"v\":1,\"source\":\"%s\",\"seq\":%" PRIu32 ",\"t_ms\":%" PRIu64 ",\"state\":\"%s\",\"points\":[", source == Source::Demo ? "demo" : "radar", frame ? frame->number : std::uint32_t{0}, now, !frame ? "unavailable" : count ? "cloud" : "no_cloud")) return 0;
    for (std::size_t i = 0; i < count; ++i) {
        const auto& p = frame->points[i];
        if (!std::isfinite(p.x_m) || !std::isfinite(p.y_m) || !std::isfinite(p.radial_velocity_mps) ||
            !append("%s[%.9g,%.9g,%.9g]", i ? "," : "", p.x_m, p.y_m, p.radial_velocity_mps)) return 0;
    }
    return append("]}\n") ? used : 0;
}
} // namespace fyp::radar
