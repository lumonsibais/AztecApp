from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

local_llm = LLM(
    model="openai/gpt-4o-mini",
    base_url="http://127.0.0.1:8080/v1",
    api_key="local",
    # Un 3B se va por las ramas con temperatura alta, y aquí solo queremos que
    # rellene el esqueleto que le da cada tarea.
    temperature=0.1,
)


@CrewBase
class AztecCrew():
    """AztecApp Backend Dev Crew."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ---------------------------------------------------------------- agents

    @agent
    def model_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["model_engineer"],
            llm=local_llm,
            verbose=True
        )

    @agent
    def service_developer(self) -> Agent:
        return Agent(
            config=self.agents_config["service_developer"],
            llm=local_llm,
            verbose=True
        )

    # ----------------------------------------------------------------- tasks
    #
    # Sin métodos @task, self.tasks queda vacío y el crew arranca y termina sin
    # generar nada. Ese era el estado hasta ahora.
    #
    # `context=[]` en todas: el proceso secuencial encadena por defecto la
    # salida de cada tarea como contexto de la siguiente, y estas seis son
    # independientes. Encadenarlas solo llena el contexto del 3B con código
    # ajeno y le hace mezclar unos modelos con otros.

    @task
    def t1_translation_model(self) -> Task:
        return Task(config=self.tasks_config["t1_translation_model"], context=[])

    @task
    def t2_translation_repository(self) -> Task:
        return Task(config=self.tasks_config["t2_translation_repository"], context=[])

    @task
    def t3_locale_middleware(self) -> Task:
        return Task(config=self.tasks_config["t3_locale_middleware"], context=[])

    @task
    def t4_lake_geometry_model(self) -> Task:
        return Task(config=self.tasks_config["t4_lake_geometry_model"], context=[])

    @task
    def t5_place_geom_column(self) -> Task:
        return Task(config=self.tasks_config["t5_place_geom_column"], context=[])

    @task
    def t6_translated_serializer(self) -> Task:
        return Task(config=self.tasks_config["t6_translated_serializer"], context=[])

    # ------------------------------------------------------------------ crew

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
