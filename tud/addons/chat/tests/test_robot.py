import os
import robotsuite
import unittest

from plone.testing import layered

from tud.addons.chat.testing import ROBOT_TESTING


def test_suite():
    """
    Sets up test suite.

    :return: test suite
    :rtype: unittest.suite.TestSuite
    """
    suite = unittest.TestSuite()
    current_dir = os.path.abspath(os.path.dirname(__file__))
    robot_dir = os.path.join(current_dir, 'robot')
    robot_tests = [
        os.path.join('robot', doc) for doc in os.listdir(robot_dir)
        if doc.endswith('.robot') and doc.startswith('test_')
    ]

    for test in robot_tests:
        suite.addTests([
            layered(robotsuite.RobotTestSuite(test),
                    layer = ROBOT_TESTING),
        ])
    return suite
