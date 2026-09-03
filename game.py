import typing
import time
import functools
import enum
import sys
import os

import numpy as np

import display_grid as dg

arrows = {
    # gravity exists but is canceled out
    (0, 0): "🮢🮣🮠🮡",

    # distance 1
    (2, 0): "  🮡🮠",
    (1, 1): "  ╶┘",
    (-1, 1): "╶┐  ",
    (-2, 0): "🮣🮢  ",
    (-1, -1): "┌╴  ",
    (1, -1): "  └╴",

    # distance 1.5
    (3, 1): "  🮡┘",
    (0, 2): " 🮢 🮠",
    (-3, 1): "🮣┐  ",
    (-3, -1): "┌🮢  ",
    (0, -2): "🮣 🮡 ",
    (3, -1): "  └🮠",

    # distance 2
    (4, 0): "🮡🮠🮡🮠",
    (2, 2): "╶┘╶┘",
    (-2, 2): "╶┐╶┐",
    (-4, 0): "🮣🮢🮣🮢",
    (-2, -2): "┌╴┌╴",
    (2, -2): "└╴└╴",
}

icon_planet = "🭆🭑🭧🭜"
icon_ship = "🭮🭬🬛🬫"
icon_goal = "🬦🬹🬉 "
icon_asteroid = "🬵🬢🬊🬆"

title_lines = [
    "  🭅████🭛 🭅🭛     🭅████🭛 🭅█  🭅🭛 🭅████🭛 🭅████🭛 🭅🭛  🭅🭛 🭅████🭛 🭅████🭛",
    " 🭋🭠     🭋🭠       🭋🭠   🭋🭠█ 🭋🭠 🭋🭠     🭋🭠     🭋🭠  🭋🭠 🭋🭠  🭋🭠   🭋🭠   ",
    " 🭅████🭛 🭅🭛       🭅🭛   🭅🭛█ 🭅🭛 🭅🭛 🭅█🭛 🭅████🭛 🭅████🭛 🭅🭛  🭅🭛   🭅🭛   ",
    "    🭋🭠 🭋🭠       🭋🭠   🭋🭠 █🭋🭠 🭋🭠  🭋🭠     🭋🭠 🭋🭠  🭋🭠 🭋🭠  🭋🭠   🭋🭠    ",
    "🭅████🭛 🭅████🭛 🭅████🭛 🭅🭛 ██🭛 🭅████🭛 🭅████🭛 🭅🭛  🭅🭛 🭅████🭛   🭅🭛    ",
]

def neighbors(a: int, b: int) -> list[tuple[int, int]]:
    return [(a + 2, b), (a + 1, b + 1), (a - 1, b + 1), (a - 2, b), (a - 1, b - 1), (a + 1, b - 1)]

def intersect(a1: int, b1: int, a2: int, b2: int) -> list[tuple[int, int]]:
    M = (a2 - a1) ** 2 + 3 * (b2 - b1) ** 2
    out = []
    for a in range(min(a1, a2) - 2, max(a1, a2) + 2):
        for b in range(min(b1, b2) - 2, max(b1, b2) + 2):
            if (a + b - a1 - b1) % 2 == 0:
                K = (a2 - a1) * (b - b1) - (b2 - b1) * (a - a1)
                L = 3 * (b2 - b1) * (b - b1) + (a2 - a1) * (a - a1)
                if 0 <= L <= M:
                    if 3 * K ** 2 < M:
                        out.append((L, (a, b)))
    out.sort()
    return [pos for _, pos in out]

def draw_hex_grid(grid: dg.Grid, offset: bool = False) -> None:
    for j, col in enumerate(grid.chars.T[:3 * max(0, (grid.shape[1] - 1) // 3) + 1]):
        col[::2] = ord("/▔▔\▁▁"[(j + 3 * offset) % 6])
        col[1::2] = ord("\▁▁/▔▔"[(j + 3 * offset) % 6])

def draw_icon(
    grid: dg.Grid, 
    pos: tuple[int, int], 
    icon: str, 
    color: typing.Optional[tuple[int, int, int]] = None,
    half: bool = False,
) -> None:
    i, j = pos
    if icon[0] != " " and not half:
        grid.chars[i, j], grid.fg[i, j] = ord(icon[0]), color
    if icon[1] != " ":
        grid.chars[i, j + 1], grid.fg[i, j + 1] = ord(icon[1]), color
    if icon[2] != " " and not half:
        grid.chars[i + 1, j], grid.fg[i + 1, j] = ord(icon[2]), color
    if icon[3] != " ":
        grid.chars[i + 1, j + 1], grid.fg[i + 1, j + 1] = ord(icon[3]), color

# generic physics object
class Body(typing.NamedTuple):
    pos: tuple[int, int]
    vel: tuple[int, int]
    grav: int
    icon: str
    color: tuple[int, int, int]
    static: bool = False

    def get_acc(self, others: list["Body"]) -> tuple[int, int]:
        acc = 0, 0
        if not self.static:
            for other in others:
                if id(other) == id(self) or not other.grav:
                    continue
                grav_field = other.grav_field
                # use reference frame where other.vel == 0 for gravity field intersection checks
                if self.vel == other.vel:
                    if self.pos in grav_field:
                         acc = acc[0] + grav_field[self.pos][0], acc[1] + grav_field[self.pos][1]
                else:
                    for pos in intersect(
                        self.pos[0], 
                        self.pos[1],
                        self.pos[0] + self.vel[0] - other.vel[0], 
                        self.pos[1] + self.vel[1] - other.vel[1],
                    ):
                        if (pos != self.pos) and pos in grav_field:
                            acc = acc[0] + grav_field[pos][0], acc[1] + grav_field[pos][1]
        return acc

    @functools.lru_cache
    def step(self, *others: "Body") -> "Body":
        acc = self.get_acc(others)
        return self._replace(
            pos=(self.pos[0] + self.vel[0], self.pos[1] + self.vel[1]), 
            vel=(self.vel[0] + acc[0], self.vel[1] + acc[1]),
        )

    def draw(self, grid: dg.Grid, fade: float = 1.0, half: bool = False) -> None:
        if fade < 0.08:
            return
        if 0 <= self.pos[0] < grid.shape[0] - 1 and 0 <= self.pos[1] < max(0, (grid.shape[1] - 1) // 3):
            draw_icon(grid, (self.pos[0], self.pos[1] * 3 + 1), self.icon, (int(self.color[0] * fade), int(self.color[1] * fade), int(self.color[2] * fade)), half=half)

    @property
    @functools.lru_cache
    def grav_field(self) -> dict[tuple[int, int], tuple[int, int]]:
        return {(self.pos[0] + a * i, self.pos[1] + b * i): (-a, -b) for a, b in neighbors(0, 0) for i in range(1, self.grav + 1)}

# only for display purposes mostly
@functools.lru_cache
def total_grav_field(*bodies: Body) -> dict[tuple[int, int], tuple[int, int]]:
    out = {}
    for body in bodies:
        for pos, (a, b) in body.grav_field.items():
            prev_grav = out.get(pos, (0, 0))
            out[pos] = prev_grav[0] + a, prev_grav[1] + b
    return out

def draw_grav_field(field: dict[tuple[int, int], tuple[int, int]], grid: dg.Grid) -> None:
    for pos, acc in field.items():
        if 0 <= pos[0] < grid.shape[0] - 1 and 0 <= pos[1] < max(0, (grid.shape[1] - 1) // 3):
            draw_icon(grid, (pos[0], 3 * pos[1] + 1), arrows.get(acc, "AAAA"), (0x66, 0x66, 0x66))

class Outcome(enum.Enum):
    RUNNING = 0
    COMPLETE = 1
    FAILED = 2

# copyable state of universe
class UniverseState(typing.NamedTuple):
    ship: Body
    targets: list[Body]
    planets: list[Body]
    fuel: int
    life_support: int
    max_fuel: int
    max_life_support: int
    outcome: Outcome
    name: str
    directive: str

    def step(self, thrust: typing.Optional[int] = None) -> "UniverseState":
        ship = self.ship if thrust is None else self.ship._replace(vel=neighbors(*self.ship.vel)[thrust])
        new_state = UniverseState(
            ship=ship.step(*self.planets),
            targets=[target.step(*self.planets) for target in self.targets],
            planets=[planet.step(*self.planets) for planet in self.planets],
            fuel=self.fuel if thrust is None else self.fuel - 1, 
            life_support=self.life_support - 1,
            max_fuel=self.max_fuel,
            max_life_support=self.max_life_support,
            outcome=self.outcome,
            name=self.name,
            directive=self.directive,
        )
        for target in new_state.targets:
            if new_state.ship.pos == target.pos and (new_state.ship.vel == target.vel or target.static):
                return new_state._replace(outcome=Outcome.COMPLETE)
        if not new_state.life_support:
            return new_state._replace(outcome=Outcome.FAILED)
        for planet in self.planets:
            if planet.pos in intersect(
                self.ship.pos[0],
                self.ship.pos[1],
                new_state.ship.pos[0] - planet.vel[0],
                new_state.ship.pos[1] - planet.vel[1],
            ):
                return new_state._replace(outcome=Outcome.FAILED)
        return new_state

    def draw_fields(self, grid: dg.Grid) -> None:
        grid.fg[:] = 0x33, 0x33, 0x33
        draw_hex_grid(grid, True)
        draw_grav_field(total_grav_field(*self.planets), grid)

    def draw_bodies(self, grid: dg.Grid, fade: float = 1.0) -> None:
        placed = set()
        for body in [*self.planets, *self.targets, self.ship]:
            body.draw(grid, fade=fade, half=body.pos in placed)
            placed.add(body.pos)


# undo-redo functionality
class Universe:
    def __init__(self, state: typing.Optional[UniverseState] = None) -> None:
        self.reset(state)

    @property
    def state(self) -> typing.Optional[UniverseState]:
        return self.past[-1] if self.past else None

    def undo(self) -> bool:
        if len(self.past) > 1:
            self.future.append(self.past.pop())
            return True
        return False

    def redo(self) -> bool:
        if self.future:
            self.past.append(self.future.pop())
            return True
        return False

    def step(self, thrust: typing.Optional[int] = None) -> bool:
        if not self.past or self.state.outcome != Outcome.RUNNING or (thrust is not None and not self.state.fuel):
            return False
        self.future = []
        self.past.append(self.state.step(thrust))

    def reset(self, state: typing.Optional[UniverseState] = None) -> None:
        self.past = [state] if state else []
        self.future = []


demo_level = UniverseState(
    ship=Body(
        (10, 9),
        (-2, 0),
        0,
        icon_ship,
        (0, 255, 0),
    ),
    targets=[],
    planets=[
        Body(
            (10, 11),
            (-2, 0),
            20,
            icon_planet,
            (255, 0, 0),
        ), 
        Body(
            (10, 15),
            (2, 0),
            20,
            icon_asteroid,
            (0, 0, 255),
        ),
    ],
    fuel=10,
    life_support=100,
    max_fuel=10,
    max_life_support=100,
    outcome=Outcome.RUNNING,
    name="00-TEST",
    directive="test 123",
)


# display code independent
# expected shape: 22x58 (21x19)
class SlingshotMap(dg.Module):
    def __init__(
        self,
        parent: dg.Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        universe: Universe = Universe(None),
    ) -> None:
        super().__init__(parent, box)
        self.universe = universe

    def _draw(self) -> None:
        if self.universe.state is not None:
            self.universe.state.draw_fields(self.grid)
            future = [self.universe.state]
            for _ in range(20):
                future.append(future[-1].step())
                if future[-1].outcome != Outcome.RUNNING:
                    break
            
            for i, frame in reversed(list(enumerate(future))):
                frame.draw_bodies(self.grid, fade=0.5 * 0.8 ** i if i else 1.0)


class SlingshotGauge(dg.Module):
    def __init__(
        self,
        parent: dg.Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        name: str = "",
        capacity: int = 10,
    ) -> None:
        super().__init__(parent, box)
        self.name = name
        self.value = self.capacity = capacity

    def _draw(self) -> None:
        value = max(0, min(self.value, self.capacity))
        # pick color based on amount left
        if value >= 0.8 * self.capacity:
            color = 0x00, 0xBB, 0x33
        elif value >= 0.6 * self.capacity:
            color = 0x99, 0xFF, 0x00
        elif value >= 0.4 * self.capacity:
            color = 0xFF, 0xFF, 0x00
        elif value >= 0.2 * self.capacity:
            color = 0xFF, 0x99, 0x00
        else:
            color = 0xFF, 0x00, 0x00

        self.grid.print(self.name, pos=(0, 0), fg=color)
        self.grid.print(f"{value} / {self.capacity}" if value else "EMPTY", pos=(1, 0), fg=color)

        if self.capacity > self.shape[1]:
            capacity = self.shape[1]
            value = int(np.ceil(value / self.capacity * self.shape[1]))
        else:
            capacity = self.capacity

        self.grid.chars[2, :capacity] = ord("🮊")
        self.grid.fg[2, :capacity] = 0x33, 0x33, 0x33
        self.grid.fg[2, :value] = color

class SlingshotDirective(dg.Module):
    def __init__(
        self,
        parent: dg.Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        text: str = ""
    ) -> None:
        super().__init__(parent, box)
        self.text = text

    def _draw(self) -> None:
        self.grid.clear()
        self.grid.chars[:] = ord("#")
        self.grid.chars[1:-1, 2:-2] = ord(" ")
        for i, line in enumerate(self.text.splitlines()):
            self.grid.print(line, pos=(2 + i, 4))

# expected shape: 14x22
class SlingshotControlPanel(dg.Module):
    def __init__(
        self,
        parent: dg.Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        universe: Universe = Universe(None),
    ) -> None:
        super().__init__(parent, box)
        self.universe = universe
        self.fuel_gauge = SlingshotGauge(
            self, 
            [-8, 1, -5, -1], 
            "FUEL", 
            self.universe.state.max_fuel if self.universe.state else 0,
        )
        self.life_support_gauge = SlingshotGauge(
            self, 
            [-4, 1, -1, -1], 
            "LIFE SUPPORT", 
            self.universe.state.max_life_support if self.universe.state else 0,
        )

    def _draw(self) -> None:
        self.grid.clear()
        status = {
            Outcome.RUNNING: "IN FLIGHT",
            Outcome.COMPLETE: "COMPLETE",
            Outcome.FAILED: "FAILED"
        }[self.universe.state.outcome]
        self.grid.print("STATUS:", pos=(1, 1))
        self.grid.print(status, pos=(2, 3))
        self.grid.print("CONTROLS:  W  ", pos=(3, 1))
        self.grid.print("THRUST-> Q ◆ E", pos=(4, 1))
        self.grid.print("COAST v  A▐🬋▌D", pos=(5, 1))
        self.grid.print("[SPACE]    S  ", pos=(6, 1))

        self.grid.print("U: UNDO", pos=(8, 1), fg=None if self.universe.past[1:] else (0x66, 0x66, 0x66))
        self.grid.print("R: REDO", pos=(9, 1), fg=None if self.universe.future else (0x66, 0x66, 0x66))
        self.grid.print("Z: RESET", pos=(10, 1))
        self.grid.print("F: INFO", pos=(11, 1))
        self.grid.print("X: EXIT", pos=(12, 1))

    def _tick(self) -> None:
        self.fuel_gauge.capacity = self.universe.state.max_fuel if self.universe.state else 0
        self.fuel_gauge.value = self.universe.state.fuel if self.universe.state else 0
        self.life_support_gauge.capacity = self.universe.state.max_life_support if self.universe.state else 0
        self.life_support_gauge.value = self.universe.state.life_support if self.universe.state else 0

class SlingshotGame(dg.Module):
    def __init__(
        self,
        parent: dg.Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        universe: Universe = Universe(),
    ) -> None:
        super().__init__(parent, box)
        self.initial_state = universe.state
        self.universe = universe
        self.directive = SlingshotDirective(self, [4, 24, -4, -6], self.initial_state.directive if self.initial_state else "")
        self.panel = SlingshotControlPanel(self, [1, 2, -1, 18], self.universe)
        self.map = SlingshotMap(self, [1, 20, -1, -2], self.universe)

    def _draw(self) -> None:
        self.grid.clear()
        self.grid.chars[:] = ord("#")

    def load_map(self, state: typing.Optional[UniverseState]) -> None:
        self.initial_state = state
        self.reset_state()

    def reset_state(self) -> None:
        self.universe.reset(self.initial_state)
        self.directive.text = self.universe.state.directive if self.universe.state else ""
        self.directive.start()

    def _handle_event(self, event: dg.Event) -> bool:
        if isinstance(event, dg.KeyEvent):
            if event.key.lower() in "sdewqa " and self.directive.paused and self.universe.state.outcome == Outcome.RUNNING:
                self.universe.step(None if event.key == " " else "sdewqa".index(event.key.lower()))
                if self.universe.state and self.universe.state.outcome == Outcome.COMPLETE:
                    self.directive.text = f"MISSION COMPLETE\n\ntime taken: {self.universe.state.max_life_support - self.universe.state.life_support}\nfuel used: {self.universe.state.max_fuel - self.universe.state.fuel}\n\npress X to return to level select\npress F to close"
                    self.directive.start()
        
                elif self.universe.state and self.universe.state.outcome == Outcome.FAILED:
                    if self.universe.state.life_support:
                        self.directive.text = "MISSION FAILED\n\nYou crashed into a planet or moon.\n\npress Z to reset simulation\npress U to undo last move\npress X to return to level select\npress F to close"
                    else:
                        self.directive.text = "MISSION FAILED\n\nYou ran out of life support.\n\npress Z to reset simulation\npress U to undo last move\npress X to return to level select\npress F to close"
                    self.directive.start()
                else:
                    self.directive.text = self.universe.state.directive
                return True
            elif event.key.lower() == "u":
                self.universe.undo()
                self.directive.text = self.universe.state.directive
                if len(self.universe.past) > 1:
                    self.directive.stop()
                return True
            elif event.key.lower() == "r" and self.directive.paused:
                self.universe.redo()
                if self.universe.state and self.universe.state.outcome == Outcome.COMPLETE:
                    self.directive.text = f"MISSION COMPLETE\n\ntime taken: {self.universe.state.max_life_support - self.universe.state.life_support}\nfuel used: {self.universe.state.max_fuel - self.universe.state.fuel}\n\npress X to return to level select\npress F to close"
                    self.directive.start()
        
                elif self.universe.state and self.universe.state.outcome == Outcome.FAILED:
                    if self.universe.state.life_support:
                        self.directive.text = "MISSION FAILED\n\nYou crashed into a planet or moon.\n\npress Z to reset simulation\npress U to undo last move\npress X to return to level select\npress F to close"
                    else:
                        self.directive.text = "MISSION FAILED\n\nYou ran out of life support.\n\npress Z to reset simulation\npress U to undo last move\npress X to return to level select\npress F to close"
                    self.directive.start()
                else:
                    self.directive.text = self.universe.state.directive
                return True
            elif event.key.lower() == "z":
                self.reset_state()
                
                return True
            elif event.key.lower() == "f":
                self.directive.paused = not self.directive.paused
                return True
            elif event.key.lower() == "x":
                self.load_map(None)
                self.stop()
                return True
        return False



class SlingshotMain(dg.Module):
    def __init__(
        self,
        parent: dg.Module,
        box: typing.Optional[tuple[int, int, int, int]] = None,
        levels: list[UniverseState] = [],
    ) -> None:
        super().__init__(parent, box)
        self.levels = levels[:]
        self.cleared = set()
        self.cur_level = 0

        self.bg_sim = demo_level
        self.bg_sim_t = 0

        self.inner_grid = dg.SubGrid(self.grid, 1, 2, -1, -2)

        self.game = SlingshotGame(self)
        self.game.stop()

    def _tick(self) -> None:
        if not self.game.paused:
            if self.game.universe.state and self.game.universe.state.outcome == Outcome.COMPLETE:
                self.cleared.add(self.cur_level)

            return
        new_t = int(time.time() * 3)
        if new_t > self.bg_sim_t:
            self.bg_sim_t = new_t
            self.bg_sim = self.bg_sim.step()

    def _draw(self) -> None:
        if not self.game.paused:
            return

        self.grid.clear()
        self.grid.chars[:] = ord("#")

        draw_hex_grid(self.inner_grid, True)
        self.grid.fg[1:-1, 2:-2] = 0x33, 0x33, 0x33

        self.bg_sim.draw_fields(self.inner_grid)
        self.bg_sim.draw_bodies(self.inner_grid, fade=0.75)

        for i, line in enumerate(title_lines):
            line_arr = np.array([ord(char) for char in line], dtype=np.int32)
            self.grid.chars[i + 2, 6: 70][line_arr != ord(" ")] = line_arr[line_arr != ord(" ")]
            self.grid.fg[i + 2, 6: 70][line_arr != ord(" ")] = 0xFF, 0xFF, 0xFF

        self.grid.print("A DISCRETE ORBITAL MECHANICS PUZZLE GAME", pos=(8, 5), fg=(0xFF, 0xFF, 0xFF), attrs=dg.TA_ITALIC)

        level_str = f"LEVEL: {self.levels[self.cur_level].name}"
        if self.cur_level in self.cleared:
            level_str += " [cleared]"
        self.grid.print(level_str, pos=(12, 9), fg=(0xFF, 0xFF, 0xFF))
        self.grid.print("press A for prev. level", pos=(14, 9), fg=(0xFF, 0xFF, 0xFF) if self.cur_level > 0 else (0x66, 0x66, 0x66))
        self.grid.print("press D for next level", pos=(15, 9), fg=(0xFF, 0xFF, 0xFF) if self.cur_level < len(self.levels) - 1 else (0x66, 0x66, 0x66))
        self.grid.print("press W or [space] to start", pos=(16, 9), fg=(0xFF, 0xFF, 0xFF))
        self.grid.print("press X to quit", pos=(17, 9), fg=(0xFF, 0xFF, 0xFF))
                

    def _handle_event(self, event: dg.Event) -> bool:
        if isinstance(event, dg.KeyEvent) and self.game.paused:
            if event.key.lower() == "a" and self.cur_level > 0:
                self.cur_level = self.cur_level - 1
                return True
            elif event.key.lower() == "d" and self.cur_level < len(self.levels) - 1:
                self.cur_level = self.cur_level + 1
                return True
            elif event.key.lower() in "w ":
                self.game.start()
                self.game.load_map(self.levels[self.cur_level])
                return True
            elif event.key.lower() == "x":
                self.stop()
                return True
        return False

levels = [
    # level 1: here to there
    UniverseState(
        Body((3, 2), (0, 0), 0, icon_ship, (0xFF, 0xFF, 0xFF)),
        [
            Body((10, 7), (0, 0), 0, icon_goal, (0x00, 0xFF, 0x00)),
        ],
        [],
        10,
        99,
        10,
        99,
        Outcome.RUNNING,
        "01: Here to There",
        """Welcome, captain!
For this training simulation, you've been
placed in charge of the orbital cruiser 
Joe McPlaceholderName. Your goal is to get
your ship to the target. You'll need to
match its speed and velocity. Keep in
mind: This ain't star wars! You can't turn
on a dime! The faded copies of your ship
show her projected trajectory.


press F to begin"""
    ),

    # level 2: asteroids
    UniverseState(
            Body((3, 2), (0, 0), 0, icon_ship, (0xFF, 0xFF, 0xFF)),
            [
                Body((5, 16), (0, 0), 0, icon_goal, (0x00, 0xFF, 0x00)),
            ],
            [
                Body((i + 1, 10 + (i % 2)), (0, 0), 0, icon_asteroid, (0x99, 0x99, 0x99))
                for i in range(13)
            ],
            10,
            30,
            10,
            30,
            Outcome.RUNNING,
            "02: Asteroid Field",
            """Hello, captain!
You'll need to navigate this asteroid
field to reach your goal. If you hit one,
you die. You'll need to navigate around
them.

Don't take too long or you'll run out of
life support!



press F to close"""
        ),

    # level 3: gravity
    UniverseState(
        Body((3, 2), (0, 0), 0, icon_ship, (0xFF, 0xFF, 0xFF)),
        [
            Body((5, 16), (0, 0), 0, icon_goal, (0x00, 0xFF, 0x00)),
        ],
        [
            Body((-25, 10), (0, 0), 500, icon_planet, (0xFF, 0x00, 0x00)),
        ],
        4,
        20,
        4,
        20,
        Outcome.RUNNING,
        "03: Gravity",
        """Hello, captain!
This level includes a gravitational field.
If your ship passes through the field,
marked by the arrows, her velocity will
change in the direction of each arrow you
pass over.

Use gravity to your advantage.
Don't fight it. Work with it!
And don't run out of fuel!

press F to close"""
    ),

    # level 4: orbit
        UniverseState(
            Body((5, 6), (0, 0), 0, icon_ship, (0xFF, 0xFF, 0xFF)),
            [
                Body((11, 14), (-1, 1), 0, icon_goal, (0x00, 0xFF, 0x00)),
            ],
            [
                Body((12, 15), (0, 0), 1, icon_planet, (0xFF, 0x00, 0x00)),
            ],
            7,
            20,
            7,
            20,
            Outcome.RUNNING,
            "04: Orbit",
            """Hello, captain!
Gravitational fields often surround
planets, like here. Thanks to this
planet's gravity, with no thrust your
ship will be able to enter a stable orbit
as shown. You'll have to time it right!





press F to close"""
        ),

# level 5: ring
    UniverseState(
        Body((7, 6), (-1, 1), 0, icon_ship, (0xFF, 0xFF, 0xFF)),
        [
            Body((5, 16), (0, 0), 0, icon_goal, (0x00, 0xFF, 0x00)),
        ],
        [
            Body((8, 7), (0, 0), 2, icon_planet, (0xFF, 0x00, 0x00)),
            Body((8, 5), (-2, 0), 0, icon_asteroid, (0xFF, 0x00, 0xFF)),
            Body((8, 9), (2, 0), 0, icon_asteroid, (0x00, 0x00, 0xFF)),
        ],
        4,
        20,
        4,
        20,
        Outcome.RUNNING,
        "05: Ring",
        """Greetings, captain!
You're in orbit of a planet with 2 moons.
Don't hit them. Time your departure!








press F to close"""
    ),

    UniverseState(
        Body((19, 6), (-2, 0), 0, icon_ship, (0xFF, 0xFF, 0xFF)),
        [
            Body((0, 5), (2, 0), 0, icon_goal, (0x00, 0xFF, 0x00)),
            Body((1, 4), (3, 1), 0, icon_goal, (0x00, 0xFF, 0x00)),
            Body((3, 4), (2, 2), 0, icon_goal, (0x00, 0xFF, 0x00)),
            Body((4, 5), (0, 2), 0, icon_goal, (0x00, 0xFF, 0x00)),
            Body((3, 6), (-1, 1), 0, icon_goal, (0x00, 0xFF, 0x00)),
            Body((1, 6), (0, 0), 0, icon_goal, (0x00, 0xFF, 0x00)),
        ],
        [
            Body((18, 5), (0, 0), 2, icon_planet, (0xFF, 0x00, 0x00)),
            Body((2, 5), (1, 1), 2, icon_planet, (0x00, 0x00, 0xFF)),
        ],
        6,
        20,
        6,
        20,
        Outcome.RUNNING,
        "06: Interplanetary",
        """Welcome, captain!
You're starting in orbit of the red
planet and your goal is to orbit the blue
one. Any low orbit around it will count.







press F to close"""
    ),

    UniverseState(
        Body((7, 6), (-1, 1), 0, icon_ship, (0xFF, 0xFF, 0xFF)),
        [
            Body((5, 16), (0, 0), 0, icon_goal, (0x00, 0xFF, 0x00), True),
            *[Body(pos, (0, 0), 0, icon_goal, (0x00, 0xFF, 0x00), True) for pos in neighbors(5, 16)]
        ],
        [
            Body((8, 7), (0, 0), 3, icon_planet, (0xFF, 0x00, 0x00)),
            Body((2, 7), (1, 1), 1, icon_asteroid, (0xFF, 0x00, 0xFF)),
        ],
        3,
        5,
        3,
        5,
        Outcome.RUNNING,
        "07: Slingshot",
        """Hello, captain!
Your life support is running out. You
need to get to your destination quickly.
You'll need to perform a slingshot.
Just land anywhere close to the target,
approach speed doesn't matter. Just get
there.




press F to close"""
    ),

    UniverseState(
        Body(
            (10, 7),
            (-2, 0),
            0,
            icon_ship,
            (0, 255, 0),
        ),
        [
            Body(
                (10, 11),
                (0, 0),
                0,
                icon_goal,
                (0, 255, 0),
            ),
        ],
        [
            Body(
                (10, 9),
                (-2, 0),
                20,
                icon_planet,
                (255, 255, 0),
            ), 
            Body(
                (10, 13),
                (2, 0),
                20,
                icon_planet,
                (255, 128, 0),
            ),
        ],
        8,
        15,
        8,
        15,
        Outcome.RUNNING,
        "08: Binary",
        """Hello, captain!
Your task is to reach the center of this
binary star system so that it can be
studied. Don't crash.

Good luck!





press F to close"""
    ),
]


if __name__ == "__main__":
    try:
        # PyInstaller creates a temporary directory and stores path in sys._MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # If sys._MEIPASS does not exist, we are in standard development mode
        base_path = os.path.abspath(".")

    font_path = os.path.join(base_path, "assets/unscii-16-full.ttf")


    with dg.PygameGrid.create([24, 80], font_path, 24) as grid:
        main_module = dg.MainModule(grid, True)

        module = SlingshotMain(
            main_module,
            levels=levels,
        )

        while not module.paused:
            main_module.tick()
            main_module.draw()
            time.sleep(0.0001)

