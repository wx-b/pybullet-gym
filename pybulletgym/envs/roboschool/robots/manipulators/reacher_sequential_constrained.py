"""
This environment is exactly like ReacherSequentialBulletEnv except that at reset
time we constrain the fingertip to only be spawned in the quadrant where the
solution is found.
We use this in BTTRFLY to evaluate how the distributions of states/actions in
training (proxy) tasks affect learning alignments and transfer performance - in
this more constrained setting, there should be less state/action overlap than
in the original where the robot is randomly, uniformly initialised.
"""

import itertools
import numpy as np

from pybulletgym.envs.roboschool.robots.robot_bases import MJCFBasedRobot


class ReacherSequentialConstrained(MJCFBasedRobot):
    TARG_LIMIT = 0.116 # gives approx 10° angles in each link

    def __init__(self):
        MJCFBasedRobot.__init__(self,
                                'reacher.xml',
                                'body0',
                                action_dim=2,
                                obs_dim=9,
                                parent_collision=False)
        self.goal_positions = np.array(
            [
                [self.TARG_LIMIT, self.TARG_LIMIT],
                [self.TARG_LIMIT, -self.TARG_LIMIT],
                [-self.TARG_LIMIT, -self.TARG_LIMIT],
                [-self.TARG_LIMIT, self.TARG_LIMIT]
            ],  # defined clockwise NE->SE->SW->NW
            dtype=np.float32
        )

    def robot_specific_reset(self, bullet_client):
        self.goal = self.goal_positions[self.np_random.randint(4)]
        self.jdict["target_x"].reset_current_position(self.goal[0], 0)
        self.jdict["target_y"].reset_current_position(self.goal[1], 0)
        self.fingertip = self.parts["fingertip"]
        self.target = self.parts["target"]
        self.central_joint = self.jdict["joint0"]
        self.elbow_joint = self.jdict["joint1"]
        self.central_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
        self.elbow_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
        while (np.multiply(np.array(self.fingertip.pose().xyz()),
                           np.array(self.target.pose().xyz())) < 0).any():
            self.central_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)
            self.elbow_joint.reset_current_position(self.np_random.uniform(low=-3.14, high=3.14), 0)

    def apply_action(self, a):
        assert (np.isfinite(a).all())
        self.central_joint.set_motor_torque(0.05 * float(np.clip(a[0], -1, +1)))
        self.elbow_joint.set_motor_torque(0.05 * float(np.clip(a[1], -1, +1)))

    def calc_state(self):
        theta, self.theta_dot = self.central_joint.current_relative_position()
        self.gamma, self.gamma_dot = self.elbow_joint.current_relative_position()
        target_x, _ = self.jdict["target_x"].current_position()
        target_y, _ = self.jdict["target_y"].current_position()
        self.to_target_vec = np.array(self.fingertip.pose().xyz()) - np.array(self.target.pose().xyz())
        return np.array([
            target_x,
            target_y,
            self.to_target_vec[0],
            self.to_target_vec[1],
            np.cos(theta),
            np.sin(theta),
            self.theta_dot,
            self.gamma,
            self.gamma_dot,
        ])

    def calc_potential(self):
        return -100 * np.linalg.norm(self.to_target_vec)
