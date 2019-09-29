from mesa import Model
from mesa.time import RandomActivation

from mesa.space import Grid
from mesa.datacollection import DataCollector

from CivilViolenceAgents import PopulationAgent, CopAgent,PropagandaAgent

from settings import POPULATION_AGENT_CLASS,PROPAGANDA_AGENT_CLASS,COP_AGENT_CLASS


class CivilViolenceModel(Model):
    """
    Model 1 from "Modeling civil violence: An agent-based computational
    approach," by Joshua Epstein.
    http://www.pnas.org/content/99/suppl_3/7243.full
    Attributes:
        height: grid height
        width: grid width
        citizen_density: approximate % of cells occupied by citizens.
        cop_density: approximate % of calles occupied by cops.
        citizen_vision: number of cells in each direction (N, S, E and W) that
            citizen can inspect
        cop_vision: number of cells in each direction (N, S, E and W) that cop
            can inspect
        legitimacy:  (L) citizens' perception of regime legitimacy, equal
            across all citizens
        max_jail_term: (J_max)
        active_threshold: if (grievance - (risk_aversion * arrest_probability))
            > threshold, citizen rebels
        arrest_prob_constant: set to ensure agents make plausible arrest
            probability estimates
        movement: binary, whether agents try to move at step end
        max_iters: model may not have a natural stopping point, so we set a
            max.

        propaganda_agent_density: % of propaganda agent

        propaganda_allowed: True if we are allowing propaganda


    """

    def __init__(
            self,
            height=40,
            width=40,
            citizen_density=60,
            cop_density=4,
            citizen_vision=7,
            cop_vision=7,
            legitimacy=82,
            max_jail_term=30,
            active_threshold=13,
            arrest_prob_constant=2.3,
            movement=True,
            max_iters=1000,
            propaganda_agent_density=10,
            propaganda_factor=1,
    ):
        super().__init__()
        self.height = height
        self.width = width
        self.citizen_density = citizen_density / 100
        self.cop_density = cop_density / 100
        self.propaganda_agent_density = propaganda_agent_density / 100
        self.citizen_vision = citizen_vision
        self.cop_vision = cop_vision
        self.legitimacy = legitimacy / 100
        self.max_jail_term = max_jail_term
        self.active_threshold = active_threshold / 100
        self.arrest_prob_constant = arrest_prob_constant
        self.movement = movement
        self.max_iters = max_iters

        # initiate the model's grid and schedule
        self.iteration = 0
        self.schedule = RandomActivation(self)
        self.grid = Grid(height, width, torus=True)

        self.propaganda_factor = propaganda_factor / 1000

        # initiate data collectors for agent state feedback
        model_reporters = {
            "Quiescent": lambda m: self.count_type_citizens(m, False),
            "Active": lambda m: self.count_type_citizens(m, True),
            "Jailed": lambda m: self.count_jailed(m),
            "Active Propaganda Agents": lambda m: self.count__active_propaganda_agent(m)}

        agent_reporters = {
            "x": lambda a: a.pos[0],
            "y": lambda a: a.pos[1],
            'breed': lambda a: a.agent_class,
            "jail_sentence": lambda a: getattr(a, 'jail_time', None),
            "active": lambda a: getattr(a, "active", None),
            "arrest_probability": lambda a: getattr(a, "arrest_probability",
                                                    None)
        }
        self.datacollector = DataCollector(model_reporters=model_reporters,
                                           agent_reporters=agent_reporters)

        unique_id = 0
        if self.cop_density + self.citizen_density + self.propaganda_agent_density > 1:
            raise ValueError(
                'Cop density + citizen density + propaganda agent density must be less than 1')

        # initialize agents in the grid with respect to the given densities
        for (contents, x, y) in self.grid.coord_iter():
            if self.random.random() < self.cop_density:
                cop = CopAgent(
                    unique_id,
                    self,
                    vision=self.cop_vision,
                    pos=(
                        x,
                        y))
                unique_id += 1
                self.grid[y][x] = cop
                self.schedule.add(cop)

            elif self.random.random() < self.cop_density + self.citizen_density:
                citizen = PopulationAgent(unique_id, self,
                                          hardship=self.random.random(),
                                          legitimacy=self.legitimacy,
                                          risk_aversion=self.random.random(),
                                          threshold=self.active_threshold,
                                          susceptibility=self.random.random(),
                                          propaganda_factor=self.propaganda_factor,
                                          vision=self.citizen_vision,
                                          pos=(x, y))
                unique_id += 1
                self.grid[y][x] = citizen
                self.schedule.add(citizen)

            elif (self.random.random() < self.cop_density + self.citizen_density + self.propaganda_agent_density):
                citizen = PropagandaAgent(unique_id, self,
                                          hardship=self.random.random(),
                                          legitimacy=self.legitimacy,
                                          risk_aversion=self.random.random(),
                                          threshold=self.active_threshold,
                                          susceptibility=self.random.random(),
                                          propaganda_factor=self.propaganda_factor,
                                          vision=self.citizen_vision,
                                          pos=(x, y))
                unique_id += 1
                self.grid[y][x] = citizen
                self.schedule.add(citizen)

        self.running = True
        self.datacollector.collect(self)

    def step(self):
        # Advance the model by one step and collect data.
        self.schedule.step()
        self.datacollector.collect(self)
        self.iteration += 1
        if self.iteration > self.max_iters:
            self.running = False

    @staticmethod
    def count_type_citizens(model, count_actives, exclude_jailed=True):
        """
        Helper method to count agents by Quiescent/Active depending on ther active flag.
        """
        count = 0
        for agent in model.schedule.agents:
            if agent.agent_class == COP_AGENT_CLASS:
                continue
            if exclude_jailed and agent.jail_time:
                continue
            if count_actives and agent.active:
                count += 1
            elif not count_actives and not agent.active:
                count += 1
        return count

    @staticmethod
    def count_jailed(model):
        """
        Helper method to count jailed agents. (Both propaganda and population)
        """
        count = 0
        for agent in model.schedule.agents:
            if agent.agent_class in [POPULATION_AGENT_CLASS, PROPAGANDA_AGENT_CLASS] and agent.jail_time:
                count += 1
        return count

    @staticmethod
    def count__active_propaganda_agent(model):
        """
        Helper method to count jailed agents. (Both propaganda and population)
        """
        count = 0
        for agent in model.schedule.agents:
            if agent.agent_class in [PROPAGANDA_AGENT_CLASS] and not agent.jail_time:
                count += 1
        return count
