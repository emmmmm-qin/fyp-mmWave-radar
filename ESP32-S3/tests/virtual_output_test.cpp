#include "virtual_output.h"
#include <cstdio>
#include <cstring>

using namespace fyp::radar;
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr, "Failed: %s\n", #x); return 1; } } while (false)

int main(int argc, char** argv) {
    DoubleClick button;
    unsigned toggles = 0;
    auto sample = [&](bool down, unsigned ms) { toggles += button.update(down, ms); };
    auto click = [&](unsigned ms) {
        sample(true, ms); sample(true, ms+40); sample(false, ms+90); sample(false, ms+130);
    };
    sample(true, 0); sample(true, 100); sample(false, 150); sample(false, 190);
    click(250); CHECK(toggles == 0); // Boot-held release is not the first click.
    sample(true, 410); sample(false, 418); sample(false, 460); CHECK(toggles == 0);
    click(490); CHECK(toggles == 1);
    click(800); click(1500); CHECK(toggles == 1); // Two isolated clicks.
    sample(true, 1600); sample(true, 1650); sample(true, 2300);
    sample(false, 2400); sample(false, 2440); CHECK(toggles == 1);
    click(2600); click(2840); CHECK(toggles == 2);

    Frame frame{};
    char line[line_capacity];
    for (unsigned tick : {0u, 19u, 20u, 39u, 40u, 59u, 60u}) {
        bool valid = virtual_frame(frame, tick);
        const unsigned phase = (tick / 20) % 3;
        CHECK(valid == (phase != 2));
        CHECK(frame.has_cloud() == (phase == 0));
        CHECK(encode(line, sizeof line, valid ? &frame : nullptr, tick * 200, Source::Demo));
        CHECK(std::strncmp(line, "R2,demo,", 8) == 0);
        CHECK(std::strstr(line, phase == 0 ? ",cloud," : phase == 1 ? ",no_cloud\n" : ",unavailable\n"));
        if (argc == 2 && std::strcmp(argv[1], "--emit") == 0) std::fputs(line, stdout);
    }
    return 0;
}
