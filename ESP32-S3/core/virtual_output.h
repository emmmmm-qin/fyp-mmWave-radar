#pragma once
#include "radar_stream.h"

namespace fyp::radar {
// Count short clicks on release so a held button cannot repeat or toggle at startup.
class DoubleClick {
public:
    bool update(bool down, std::uint64_t now) {
        if (down != raw_) { raw_ = down; changed_ = now; }
        if (now - changed_ < 30) return false;
        if (!armed_) {
            if (!down) armed_ = true;
            return false;
        }
        if (stable_ == down) return false;
        stable_ = down;
        if (down) { pressed_ = now; return false; }
        if (now - pressed_ > 450) { pending_ = false; return false; }
        if (pending_ && now - released_ <= 550) { pending_ = false; return true; }
        pending_ = true;
        released_ = now;
        return false;
    }
private:
    bool raw_ = false, stable_ = false, armed_ = false, pending_ = false;
    std::uint64_t changed_ = 0, pressed_ = 0, released_ = 0;
};

// 5 Hz; each four-second phase exercises a different viewer state.
inline bool virtual_frame(Frame& f, std::uint32_t tick) {
    const auto phase = (tick / 20) % 3;
    f.number = tick + 1;
    f.major_count = phase == 0 ? 1 : 0;
    f.minor_count = 0;
    f.reported_point_count = f.major_count;
    if (phase == 0) {
        f.points[0] = {};
        f.points[0].x_m = -0.95f + 0.1f * (tick % 20);
        f.points[0].y_m = 1.5f + 0.04f * (tick % 20);
        f.points[0].radial_velocity_mps = 0.2f;
    }
    return phase != 2; // false requests an unavailable heartbeat, not a vacant room.
}
} // namespace fyp::radar
