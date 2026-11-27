#include "presence.h"

namespace fyp {

PresenceMonitor::PresenceMonitor(Config config) : config_(config) {}

void PresenceMonitor::reset()
{
    presence_ = Presence::Unavailable;
    has_observation_ = false;
    last_timestamp_ms_ = 0;
    candidate_ = false;
    candidate_count_ = 0;
}

Result PresenceMonitor::unavailable()
{
    reset();
    return {Presence::Unavailable, false, 0};
}

Result PresenceMonitor::update(const Observation& observation)
{
    if (config_.stale_after_ms == 0 || config_.occupied_confirm_frames == 0 ||
        config_.vacant_confirm_frames == 0 || !observation.valid) {
        return unavailable();
    }

    if (has_observation_) {
        if (observation.timestamp_ms <= last_timestamp_ms_) {
            return unavailable();
        }
        if (observation.timestamp_ms - last_timestamp_ms_ >= config_.stale_after_ms) {
            reset();
        }
    }

    has_observation_ = true;
    last_timestamp_ms_ = observation.timestamp_ms;
    if (candidate_count_ == 0 || candidate_ != observation.presence_detected) {
        candidate_ = observation.presence_detected;
        candidate_count_ = 1;
    } else if (candidate_count_ < UINT32_MAX) {
        ++candidate_count_;
    }

    const uint32_t required = candidate_ ? config_.occupied_confirm_frames
                                         : config_.vacant_confirm_frames;
    if (candidate_count_ >= required) {
        presence_ = candidate_ ? Presence::Occupied : Presence::Vacant;
    }
    return {presence_, true, 0};
}

Result PresenceMonitor::poll(uint64_t now_ms)
{
    if (!has_observation_ || now_ms < last_timestamp_ms_) {
        return unavailable();
    }
    const uint64_t age_ms = now_ms - last_timestamp_ms_;
    if (age_ms >= config_.stale_after_ms) {
        return unavailable();
    }
    return {presence_, true, age_ms};
}

const char* to_string(Presence presence)
{
    switch (presence) {
    case Presence::Unavailable: return "UNAVAILABLE";
    case Presence::Vacant: return "VACANT";
    case Presence::Occupied: return "OCCUPIED";
    }
    return "UNAVAILABLE";
}

} // namespace fyp
