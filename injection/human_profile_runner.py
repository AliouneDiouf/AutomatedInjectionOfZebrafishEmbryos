# injection/human_profile_runner.py

import time


class HumanProfileRunner:
    """
    Exécute l'injection sur l'Arduino via une commande unique 'inject'
    puis déclenche le retreat (retour HOME) via AS5600.
    """
    def __init__(self, injector_ctrl):
        self.injector = injector_ctrl  # hardware.InjectorController

    def run(self, retreat_home_angle=None, retreat_epsilon=2.0, retreat_speed=400, retreat_max_time=6.0):
        # Arduino autonomous injection
        self.injector.send_safe("inject")
        time.sleep(0.35)

        # Safety stop
        self.injector.send_safe("setSpeed 0")
        self.injector.send_safe("end_profile")

        # Small wait after injection
        time.sleep(2.0)

        # Retreat if home known
        if retreat_home_angle is not None:
            self.injector.retreat_to_home(
                home_angle=retreat_home_angle,
                epsilon=retreat_epsilon,
                speed=retreat_speed,
                max_time=retreat_max_time
            )
