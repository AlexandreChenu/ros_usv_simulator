#!/usr/bin/env python
# coding=utf-8

# Node ROS simu_thruster

# S'abonne aux commande et position moteur pour traduire ça en
# force et en moment sur le système


import rospy
import numpy as np
from std_msgs.msg import Int16
from geometry_msgs.msg import WrenchStamped
from geometry_msgs.msg import Quaternion
import tf

class SimDynMot():

    def __init__(self, config):
        self.config = config

        # initialisation des commandes
        self.cmd_thrust = 0

        self.orientation = Quaternion()
        quaternion = tf.transformations.quaternion_from_euler(0, 0, 0)
        self.orientation.x = quaternion[0]
        self.orientation.y = quaternion[1]
        self.orientation.z = quaternion[2]
        self.orientation.w = quaternion[3]

        self.wrenchThruster = WrenchStamped()

    def update_orientation(self, msg):
        self.orientation = msg

    def update_cmd_thrust(self, msg):
        self.cmd_thrust = msg.data
        self.process()

    def process_force(self, commande):
        # La commande est de -1 à 1
        # Pour les moteurs on est habituellement sur une courbe quadratique de puissance
        y = 0.1
        thrust = self.config['type']['max_force']*(y*commande**2 + (1-y)*commande)

        return thrust

    def process(self):
        # Traduction pwm->[-1;1]
        cmd_thrust = (self.cmd_thrust-1500)/500.0

        # Gestion des quaternions
        print 'self.orientation:', self.orientation, self.orientation.__class__
        quaternion = (self.orientation.x, self.orientation.y, self.orientation.z, self.orientation.w)
        euler = tf.transformations.euler_from_quaternion(quaternion)
        yaw = euler[0]
        pitch = euler[1]
        roll = euler[2]

        # Calcul de la force
        thrust = self.process_force(cmd_thrust)
        self.wrenchThruster.wrench.force.x = thrust * np.cos(yaw)
        self.wrenchThruster.wrench.force.y = thrust * np.sin(yaw)
        self.wrenchThruster.wrench.force.z = 0

        # la force s'applique en (x,y) avec un angle a par rapport au cap du vehicule.
        # x est la coordonnee le long du vehicule
        self.wrenchThruster.wrench.torque.z = self.wrenchThruster.wrench.force.y*self.config['position']['x'] \
                                            + self.wrenchThruster.wrench.force.x*self.config['position']['y']

        pub_force.publish(self.wrenchThruster)


if __name__ == '__main__':
    rospy.init_node('simu_thruster')

    # === COMMON ===

    # La node doit se lancer en sachant où chercher sa config. Le nom du noeud est géré par le launcher
    node_name = rospy.get_name()
    device_type_name = rospy.get_param(node_name+'_type_name')

    # Config
    ns = rospy.get_namespace()
    nslen = len(ns)
    prefix_len = nslen + 5 # On enlève le namespace et simu_
    config_node = rospy.get_param('robot/'+device_type_name+'/'+node_name[prefix_len:])
    print config_node

    # Pas sur qu'on en ai besoin mais au cas où
    device_type = config_node['type']
    config_device = rospy.get_param('device_types/'+device_type)
    print config_device

    # === SPECIFIC ===

    # Fusion
    config_node['type'] = config_device

    # Recuperation des parametres
    pin = config_node['command']['pwm']['pin']

    simu = SimDynMot(config_node)

    # sub pub
    sub_yaw = rospy.Subscriber('orientation', Quaternion, simu.update_orientation) # Eventuellement la node qui est l'actionneur placé avant le moteur a son propre temps. Ou sinon il y a une node qui donne le temps et qui synchronise les simulation (mieux)
    sub_pwm_cmd = rospy.Subscriber('pwm_out_'+str(pin), Int16, simu.update_cmd_thrust)
    pub_force = rospy.Publisher('force_'+node_name[prefix_len:], WrenchStamped, queue_size=1)

    rospy.spin()
