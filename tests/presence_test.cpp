#include "presence.h"

#include <cstdio>
#include <cstdlib>

using fyp::Presence;
using fyp::PresenceMonitor;

namespace {
int failures = 0;

void check(bool condition, const char* label)
{
    if (!condition) {
        std::printf("FAIL: %s\n", label);
        ++failures;
    }
}
}

int main()
{
    const fyp::Config config{1000, 2, 3};
    PresenceMonitor monitor(config);
    auto result = monitor.poll(0);
    check(result.presence == Presence::Unavailable && !result.has_observation,
          "no input is unavailable");

    result = monitor.update({100, true, true});
    check(result.presence == Presence::Unavailable && result.has_observation,
          "first occupied sample does not confirm");
    result = monitor.update({200, true, true});
    check(result.presence == Presence::Occupied, "occupied confirmation");
    result = monitor.poll(300);
    check(result.presence == Presence::Occupied && result.age_ms == 100,
          "fresh age and retained state");
    check(monitor.update({400, true, false}).presence == Presence::Occupied,
          "vacancy must be confirmed");
    check(monitor.update({500, true, false}).presence == Presence::Occupied,
          "vacancy still pending");
    check(monitor.update({600, true, false}).presence == Presence::Vacant,
          "vacancy confirmation");
    check(monitor.poll(1599).presence == Presence::Vacant, "fresh before boundary");
    check(monitor.poll(1600).presence == Presence::Unavailable, "stale boundary");
    check(monitor.update({1700, true, false}).presence == Presence::Unavailable,
          "stale reset requires confirmation");
    check(monitor.update({1800, false, false}).presence == Presence::Unavailable,
          "invalid input is not vacant");
    check(!monitor.poll(1801).has_observation, "invalid clears observation");

    check(monitor.update({1900, true, true}).presence == Presence::Unavailable,
          "confirmation restarts after invalid");
    check(monitor.update({2000, true, true}).presence == Presence::Occupied,
          "occupied after recovery");
    check(monitor.update({2000, true, true}).presence == Presence::Unavailable,
          "duplicate timestamp rejected");
    monitor.update({2100, true, true});
    check(monitor.update({2099, true, true}).presence == Presence::Unavailable,
          "decreasing timestamp rejected");
    monitor.update({2200, true, true});
    check(monitor.poll(2199).presence == Presence::Unavailable,
          "clock regression rejected");
    monitor.update({2300, true, true});
    check(monitor.update({3300, true, true}).presence == Presence::Unavailable,
          "gap resets before accepting new sample");
    check(monitor.update({3400, true, true}).presence == Presence::Occupied,
          "new samples reconfirm after gap");

    PresenceMonitor invalid_config({0, 2, 3});
    check(invalid_config.update({1, true, false}).presence == Presence::Unavailable,
          "zero stale interval fails closed");
    PresenceMonitor invalid_count({1000, 0, 3});
    check(invalid_count.update({1, true, true}).presence == Presence::Unavailable,
          "zero confirmation count fails closed");

    if (failures != 0) {
        std::printf("%d checks failed\n", failures);
        return EXIT_FAILURE;
    }
    std::puts("PASS: synthetic presence checks");
    return EXIT_SUCCESS;
}
