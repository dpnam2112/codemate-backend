from core.utils.decorators import singleton
from machine.services.workflows.lp_recommender import lp_recommender_workflow_factory


@singleton
class ServiceProvider:
    def __init__(self): pass

    def get_lp_recommender_workflow(self):
        return lp_recommender_workflow_factory()

    def get_learning_resource_kg_builder(self):
        return 
