#pragma once

#include <cstdint>

namespace fyp {

enum class Presence { Unavailable, Vacant, Occupied };

struct Observation {
    uint64_t timestamp_ms;
    bool valid;
    bool presence_detected;
};

struct Config {
    uint64_t stale_after_ms;
    uint32_t occupied_confirm_frames;
    uint32_t vacant_confirm_frames;
};

struct Result {
    Presence presence;
    bool has_observation;
    uint64_t age_ms;
};

class PresenceMonitor {
public:
    explicit PresenceMonitor(Config config);
    Result update(const Observation& observation);
    Result poll(uint64_t now_ms);
    void reset();

private:
    Result unavailable();
    Config config_;
    Presence presence_ = Presence::Unavailable;
    bool has_observation_ = false;
    uint64_t last_timestamp_ms_ = 0;
    bool candidate_ = false;
    uint32_t candidate_count_ = 0;
};

const char* to_string(Presence presence);

} // namespace fyp
