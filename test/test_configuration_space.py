# Copyright (c) 2014-2016, ConfigSpace developers
# Matthias Feurer
# Katharina Eggensperger
# and others (see commit history).
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from collections import OrderedDict
from itertools import product
import json
import sys
import unittest

import numpy as np

from ConfigSpace import ConfigurationSpace, \
    Configuration, CategoricalHyperparameter, UniformIntegerHyperparameter, \
    Constant, EqualsCondition, NotEqualsCondition, InCondition, \
    AndConjunction, OrConjunction, ForbiddenEqualsClause, \
    ForbiddenAndConjunction, UniformFloatHyperparameter
from ConfigSpace.hyperparameters import NormalFloatHyperparameter


def byteify(input):
    print(sys.version)
    if sys.version_info >= (3, 0):
        return input

    # From http://stackoverflow.com/a/13105359/4636294
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


class TestConfigurationSpace(unittest.TestCase):
    # TODO generalize a few simple configuration spaces which are used over
    # and over again throughout this test suite
    # TODO make sure that every function here tests one aspect of the
    # configuration space object!
    def test_add_hyperparameter(self):
        cs = ConfigurationSpace()
        hp = UniformIntegerHyperparameter("name", 0, 10)
        cs.add_hyperparameter(hp)

    def test_add_non_hyperparameter(self):
        cs = ConfigurationSpace()
        non_hp = unittest.TestSuite()
        self.assertRaises(TypeError, cs.add_hyperparameter, non_hp)

    def test_add_hyperparameters_with_equal_names(self):
        cs = ConfigurationSpace()
        hp = UniformIntegerHyperparameter("name", 0, 10)
        cs.add_hyperparameter(hp)
        self.assertRaisesRegexp(ValueError,
                                "Hyperparameter 'name' is already in the "
                                "configuration space.",
                                cs.add_hyperparameter, hp)

    def test_illegal_default_configuration(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("loss", ["l1", "l2"], default='l1')
        hp2 = CategoricalHyperparameter("penalty", ["l1", "l2"], default='l1')
        cs.add_hyperparameter(hp1)
        cs.add_hyperparameter(hp2)
        forb1 = ForbiddenEqualsClause(hp1, "l1")
        forb2 = ForbiddenEqualsClause(hp2, "l1")
        forb3 = ForbiddenAndConjunction(forb1, forb2)
        # cs.add_forbidden_clause(forb3)
        self.assertRaisesRegexp(ValueError, "Given vector violates forbidden clause \(Forbidden: loss == \'l1\' && "
            "Forbidden: penalty == \'l1\'\)", cs.add_forbidden_clause, forb3)

    def test_add_non_condition(self):
        cs = ConfigurationSpace()
        non_cond = unittest.TestSuite()
        self.assertRaises(TypeError, cs.add_condition, non_cond)

    def test_hyperparameters_with_valid_condition(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)
        cond = EqualsCondition(hp2, hp1, 0)
        cs.add_condition(cond)
        self.assertEqual(len(cs._hyperparameters), 2)

    def test_condition_without_added_hyperparameters(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cond = EqualsCondition(hp2, hp1, 0)
        self.assertRaisesRegexp(ValueError, "Child hyperparameter 'child' not "
                                "in configuration space.", cs.add_condition,
                                cond)
        cs.add_hyperparameter(hp1)
        self.assertRaisesRegexp(ValueError, "Child hyperparameter 'child' not "
                                "in configuration space.", cs.add_condition,
                                cond)

        # Test also the parent hyperparameter
        cs2 = ConfigurationSpace()
        cs2.add_hyperparameter(hp2)
        self.assertRaisesRegexp(ValueError, "Parent hyperparameter 'parent' "
                                "not in configuration space.",
                                cs2.add_condition, cond)

    def test_condition_with_cycles(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)
        cond1 = EqualsCondition(hp2, hp1, 0)
        cs.add_condition(cond1)
        cond2 = EqualsCondition(hp1, hp2, 0)
        self.assertRaisesRegexp(ValueError, "Hyperparameter configuration "
                                "contains a cycle \[\['child', 'parent'\]\]",
                                cs.add_condition, cond2)

    def test_add_conjunction(self):
        hp1 = CategoricalHyperparameter("input1", [0, 1])
        hp2 = CategoricalHyperparameter("input2", [0, 1])
        hp3 = CategoricalHyperparameter("input3", [0, 1])
        hp4 = Constant("And", "True")

        cond1 = EqualsCondition(hp4, hp1, 1)
        cond2 = EqualsCondition(hp4, hp2, 1)
        cond3 = EqualsCondition(hp4, hp3, 1)

        andconj1 = AndConjunction(cond1, cond2, cond3)

        cs = ConfigurationSpace()
        cs.add_hyperparameter(hp1)
        cs.add_hyperparameter(hp2)
        cs.add_hyperparameter(hp3)
        cs.add_hyperparameter(hp4)

        cs.add_condition(andconj1)
        self.assertNotIn(hp4, cs.get_all_unconditional_hyperparameters())

    def test_add_second_condition_wo_conjunction(self):
        hp1 = CategoricalHyperparameter("input1", [0, 1])
        hp2 = CategoricalHyperparameter("input2", [0, 1])
        hp3 = Constant("And", "True")

        cond1 = EqualsCondition(hp3, hp1, 1)
        cond2 = EqualsCondition(hp3, hp2, 1)

        cs = ConfigurationSpace()
        cs.add_hyperparameter(hp1)
        cs.add_hyperparameter(hp2)
        cs.add_hyperparameter(hp3)

        cs.add_condition(cond1)
        self.assertRaisesRegexp(ValueError,
                                "Adding a second condition \(different\) for a "
                                "hyperparameter is ambigouos and "
                                "therefore forbidden. Add a conjunction "
                                "instead!",
                                cs.add_condition, cond2)

    def test_add_forbidden_clause(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("input1", [0, 1])
        cs.add_hyperparameter(hp1)
        forb = ForbiddenEqualsClause(hp1, 1)
        # TODO add checking whether a forbidden clause makes sense at all
        cs.add_forbidden_clause(forb)
        # TODO add something to properly retrieve the forbidden clauses
        self.assertEqual(str(cs), "Configuration space object:\n  "
                                  "Hyperparameters:\n    input1, "
                                  "Type: Categorical, Choices: {0, 1}, "
                                  "Default: 0\n"
                                  "  Forbidden Clauses:\n"
                                  "    Forbidden: input1 == 1\n")

    def test_add_configuration_space(self):
        cs = ConfigurationSpace()
        hp1 = cs.add_hyperparameter(CategoricalHyperparameter("input1", [0, 1]))
        forb1 = cs.add_forbidden_clause(ForbiddenEqualsClause(hp1, 1))
        hp2 = cs.add_hyperparameter(UniformIntegerHyperparameter("child", 0, 10))
        cond = cs.add_condition(EqualsCondition(hp2, hp1, 0))
        cs2 = ConfigurationSpace()
        cs2.add_configuration_space('prefix', cs, delimiter='__')
        self.assertEqual(str(cs2), '''Configuration space object:
  Hyperparameters:
    prefix__child, Type: UniformInteger, Range: [0, 10], Default: 5
    prefix__input1, Type: Categorical, Choices: {0, 1}, Default: 0
  Conditions:
    prefix__child | prefix__input1 == 0
  Forbidden Clauses:
    Forbidden: prefix__input1 == 1
''')

    def test_get_hyperparameters(self):
        cs = ConfigurationSpace()
        self.assertEqual(0, len(cs.get_hyperparameters()))
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        self.assertEqual([hp1], cs.get_hyperparameters())
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)
        cond1 = EqualsCondition(hp2, hp1, 1)
        cs.add_condition(cond1)
        self.assertEqual([hp1, hp2], cs.get_hyperparameters())
        # TODO: I need more tests for the topological sort!
        self.assertEqual([hp1, hp2], cs.get_hyperparameters())

    def test_get_hyperparameters_topological_sort_simple(self):
        for iteration in range(10):
            cs = ConfigurationSpace()
            hp1 = CategoricalHyperparameter("parent", [0, 1])
            cs.add_hyperparameter(hp1)
            hp2 = UniformIntegerHyperparameter("child", 0, 10)
            cs.add_hyperparameter(hp2)
            cond1 = EqualsCondition(hp2, hp1, 0)
            cs.add_condition(cond1)
            # This automatically checks the configuration!
            Configuration(cs, dict(parent=0, child=5))

    def test_get_hyperparameters_topological_sort(self):
            # and now for something more complicated
            cs = ConfigurationSpace()
            hp1 = CategoricalHyperparameter("input1", [0, 1])
            hp2 = CategoricalHyperparameter("input2", [0, 1])
            hp3 = CategoricalHyperparameter("input3", [0, 1])
            hp4 = CategoricalHyperparameter("input4", [0, 1])
            hp5 = CategoricalHyperparameter("input5", [0, 1])
            hp6 = Constant("AND", "True")
            # More top-level hyperparameters
            hp7 = CategoricalHyperparameter("input7", [0, 1])
            # Somewhat shuffled
            hyperparameters = [hp1, hp2, hp3, hp4, hp5, hp6, hp7]

            for hp in hyperparameters:
                cs.add_hyperparameter(hp)

            cond1 = EqualsCondition(hp6, hp1, 1)
            cond2 = NotEqualsCondition(hp6, hp2, 1)
            cond3 = InCondition(hp6, hp3, [1])
            cond4 = EqualsCondition(hp5, hp3, 1)
            cond5 = EqualsCondition(hp4, hp5, 1)
            cond6 = EqualsCondition(hp6, hp4, 1)
            cond7 = EqualsCondition(hp6, hp5, 1)

            conj1 = AndConjunction(cond1, cond2)
            conj2 = OrConjunction(conj1, cond3)
            conj3 = AndConjunction(conj2, cond6, cond7)

            cs.add_condition(cond4)
            hps = cs.get_hyperparameters()
            # AND is moved to the front because of alphabetical sorting
            for hp, idx in zip(hyperparameters, [1, 2, 3, 4, 6, 0, 5]):
                self.assertEqual(hps.index(hp), idx)
                self.assertEqual(cs._hyperparameter_idx[hp.name], idx)
                self.assertEqual(cs._idx_to_hyperparameter[idx], hp.name)

            cs.add_condition(cond5)
            hps = cs.get_hyperparameters()
            for hp, idx in zip(hyperparameters, [1, 2, 3, 6, 5, 0, 4]):
                self.assertEqual(hps.index(hp), idx)
                self.assertEqual(cs._hyperparameter_idx[hp.name], idx)
                self.assertEqual(cs._idx_to_hyperparameter[idx], hp.name)

            cs.add_condition(conj3)
            hps = cs.get_hyperparameters()
            print(hps, hyperparameters)
            for hp, idx in zip(hyperparameters, [0, 1, 2, 5, 4, 6, 3]):
                print(hp, idx)
                self.assertEqual(hps.index(hp), idx)
                self.assertEqual(cs._hyperparameter_idx[hp.name], idx)
            self.assertEqual(cs._idx_to_hyperparameter[idx], hp.name)

    def test_get_hyperparameter(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)

        retval = cs.get_hyperparameter("parent")
        self.assertEqual(hp1, retval)
        retval = cs.get_hyperparameter("child")
        self.assertEqual(hp2, retval)
        self.assertRaises(KeyError, cs.get_hyperparameter, "grandfather")

    def test_get_conditions(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)
        self.assertEqual([], cs.get_conditions())
        cond1 = EqualsCondition(hp2, hp1, 0)
        cs.add_condition(cond1)
        self.assertEqual([cond1], cs.get_conditions())

    def test_get_parent_and_chil_conditions_of(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)
        cond1 = EqualsCondition(hp2, hp1, 0)
        cs.add_condition(cond1)

        self.assertEqual([cond1], cs.get_parent_conditions_of(hp2.name))
        self.assertEqual([cond1], cs.get_parent_conditions_of(hp2))
        self.assertEqual([cond1], cs.get_child_conditions_of(hp1.name))
        self.assertEqual([cond1], cs.get_child_conditions_of(hp1))

        self.assertRaisesRegexp(KeyError,
                                "Hyperparameter 'Foo' does not exist in this "
                                "configuration space.", cs.get_parents_of,
                                "Foo")
        self.assertRaisesRegexp(KeyError,
                                "Hyperparameter 'Foo' does not exist in this "
                                "configuration space.", cs.get_children_of,
                                "Foo")

    def test_get_parent_and_children_of(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)
        cond1 = EqualsCondition(hp2, hp1, 0)
        cs.add_condition(cond1)

        self.assertEqual([hp1], cs.get_parents_of(hp2.name))
        self.assertEqual([hp1], cs.get_parents_of(hp2))
        self.assertEqual([hp2], cs.get_children_of(hp1.name))
        self.assertEqual([hp2], cs.get_children_of(hp1))

        self.assertRaisesRegexp(KeyError,
                                "Hyperparameter 'Foo' does not exist in this "
                                "configuration space.", cs.get_parents_of,
                                "Foo")
        self.assertRaisesRegexp(KeyError,
                                "Hyperparameter 'Foo' does not exist in this "
                                "configuration space.", cs.get_children_of,
                                "Foo")

    def test_check_configuration_input_checking(self):
        cs = ConfigurationSpace()
        self.assertRaisesRegexp(TypeError, "The method check_configuration must be called "
                                            "with an instance of %s. "
                                            "Your input was of type %s"% (Configuration, type("String")),
                                cs.check_configuration, "String")
        # For the check configuration method with vector representation
        self.assertRaisesRegexp(TypeError, "The method check_configuration must"
                                           " be called with an instance of "
                                           "np.ndarray Your input was of type %s" % (type("String")),
                                cs.check_configuration_vector_representation, "String")

    def test_check_configuration(self):
        # TODO this is only a smoke test
        # TODO actually, this rather tests the evaluate methods in the
        # conditions module!
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)
        cond1 = EqualsCondition(hp2, hp1, 0)
        cs.add_condition(cond1)
        # This automatically checks the configuration!
        Configuration(cs, dict(parent=0, child=5))

        # and now for something more complicated
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("input1", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = CategoricalHyperparameter("input2", [0, 1])
        cs.add_hyperparameter(hp2)
        hp3 = CategoricalHyperparameter("input3", [0, 1])
        cs.add_hyperparameter(hp3)
        hp4 = CategoricalHyperparameter("input4", [0, 1])
        cs.add_hyperparameter(hp4)
        hp5 = CategoricalHyperparameter("input5", [0, 1])
        cs.add_hyperparameter(hp5)
        hp6 = Constant("AND", "True")
        cs.add_hyperparameter(hp6)

        cond1 = EqualsCondition(hp6, hp1, 1)
        cond2 = NotEqualsCondition(hp6, hp2, 1)
        cond3 = InCondition(hp6, hp3, [1])
        cond4 = EqualsCondition(hp6, hp4, 1)
        cond5 = EqualsCondition(hp6, hp5, 1)

        conj1 = AndConjunction(cond1, cond2)
        conj2 = OrConjunction(conj1, cond3)
        conj3 = AndConjunction(conj2, cond4, cond5)
        cs.add_condition(conj3)

        expected_outcomes = [False, False, False, False, False,
                             False, False, True, False, False,
                             False, False, False, False, False,
                             True, False, False, False, True,
                             False, False, False, True, False,
                             False, False, False, False, False,
                             False, True]

        for idx, values in enumerate(product([0, 1], repeat=5)):
            # The hyperparameters aren't sorted, but the test assumes them to
            #  be sorted.
            hyperparameters = sorted(cs.get_hyperparameters(),
                                     key=lambda t: t.name)
            instantiations = {hyperparameters[jdx+1].name: values[jdx]
                              for jdx in range(len(values))}

            evaluation = conj3.evaluate(instantiations)
            self.assertEqual(expected_outcomes[idx], evaluation)

            if evaluation == False:
                self.assertRaisesRegexp(ValueError,
                                        "Inactive hyperparameter 'AND' must "
                                        "not be specified, but has the vector value: "
                                        "'0.0'.",
                                        Configuration, cs, values={
                                        "input1": values[0],
                                        "input2": values[1],
                                        "input3": values[2],
                                        "input4": values[3],
                                        "input5": values[4],
                                        "AND": "True"})
            else:
                Configuration(cs, values={"input1": values[0],
                                          "input2": values[1],
                                          "input3": values[2],
                                          "input4": values[3],
                                          "input5": values[4],
                                          "AND": "True"})

    def test_check_configuration2(self):
        # Test that hyperparameters which are not active must not be set and
        # that evaluating forbidden clauses does not choke on missing
        # hyperparameters
        cs = ConfigurationSpace()
        classifier = CategoricalHyperparameter("classifier",
            ["k_nearest_neighbors", "extra_trees"])
        metric = CategoricalHyperparameter("metric", ["minkowski", "other"])
        p = CategoricalHyperparameter("k_nearest_neighbors:p", [1, 2])
        metric_depends_on_classifier = EqualsCondition(metric, classifier,
                                                       "k_nearest_neighbors")
        p_depends_on_metric = EqualsCondition(p, metric, "minkowski")
        cs.add_hyperparameter(metric)
        cs.add_hyperparameter(p)
        cs.add_hyperparameter(classifier)
        cs.add_condition(metric_depends_on_classifier)
        cs.add_condition(p_depends_on_metric)

        forbidden = ForbiddenEqualsClause(metric, "other")
        cs.add_forbidden_clause(forbidden)

        configuration = Configuration(cs, dict(classifier="extra_trees"))

        # check backward compatibility with checking configurations instead of vectors
        cs.check_configuration(configuration)

    def test_check_forbidden_with_sampled_vector_configuration(self):
        cs = ConfigurationSpace()
        metric = CategoricalHyperparameter("metric", ["minkowski", "other"])
        cs.add_hyperparameter(metric)

        forbidden = ForbiddenEqualsClause(metric, "other")
        cs.add_forbidden_clause(forbidden)
        configuration = Configuration(cs,
            vector=np.ones(1, dtype=float))
        self.assertRaisesRegexp(ValueError, "violates forbidden clause",
                                cs._check_forbidden, configuration.get_array())

    def test_eq(self):
        # Compare empty configuration spaces
        cs1 = ConfigurationSpace()
        cs2 = ConfigurationSpace()
        self.assertEqual(cs1, cs2)

        # Compare to something which isn't a configuration space
        self.assertTrue(not (cs1 == "ConfigurationSpace"))

        # Compare to equal configuration spaces
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        hp3 = UniformIntegerHyperparameter("friend", 0, 5)
        cond1 = EqualsCondition(hp2, hp1, 0)
        cs1.add_hyperparameter(hp1)
        cs1.add_hyperparameter(hp2)
        cs1.add_condition(cond1)
        cs2.add_hyperparameter(hp1)
        cs2.add_hyperparameter(hp2)
        cs2.add_condition(cond1)
        self.assertEqual(cs1, cs2)
        cs1.add_hyperparameter(hp3)
        self.assertFalse(cs1 == cs2)

    def test_neq(self):
        cs1 = ConfigurationSpace()
        self.assertNotEqual(cs1, "ConfigurationSpace")

    def test_repr(self):
        cs1 = ConfigurationSpace()
        retval = cs1.__str__()
        self.assertEqual("Configuration space object:\n  Hyperparameters:\n",
                         retval)

        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs1.add_hyperparameter(hp1)
        retval = cs1.__str__()
        self.assertEqual("Configuration space object:\n  Hyperparameters:\n"
                         "    %s\n" % str(hp1), retval)

        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cond1 = EqualsCondition(hp2, hp1, 0)
        cs1.add_hyperparameter(hp2)
        cs1.add_condition(cond1)
        retval = cs1.__str__()
        self.assertEqual("Configuration space object:\n  Hyperparameters:\n"
                         "    %s\n    %s\n  Conditions:\n    %s\n" %
                         (str(hp2), str(hp1), str(cond1)), retval)

    def test_sample_configuration(self):
        cs = ConfigurationSpace()
        hp1 = CategoricalHyperparameter("parent", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = UniformIntegerHyperparameter("child", 0, 10)
        cs.add_hyperparameter(hp2)
        cond1 = EqualsCondition(hp2, hp1, 0)
        cs.add_condition(cond1)
        # This automatically checks the configuration!
        Configuration(cs, dict(parent=0, child=5))

        # and now for something more complicated
        cs = ConfigurationSpace(seed=1)
        hp1 = CategoricalHyperparameter("input1", [0, 1])
        cs.add_hyperparameter(hp1)
        hp2 = CategoricalHyperparameter("input2", [0, 1])
        cs.add_hyperparameter(hp2)
        hp3 = CategoricalHyperparameter("input3", [0, 1])
        cs.add_hyperparameter(hp3)
        hp4 = CategoricalHyperparameter("input4", [0, 1])
        cs.add_hyperparameter(hp4)
        hp5 = CategoricalHyperparameter("input5", [0, 1])
        cs.add_hyperparameter(hp5)
        hp6 = Constant("AND", "True")
        cs.add_hyperparameter(hp6)

        cond1 = EqualsCondition(hp6, hp1, 1)
        cond2 = NotEqualsCondition(hp6, hp2, 1)
        cond3 = InCondition(hp6, hp3, [1])
        cond4 = EqualsCondition(hp5, hp3, 1)
        cond5 = EqualsCondition(hp4, hp5, 1)
        cond6 = EqualsCondition(hp6, hp4, 1)
        cond7 = EqualsCondition(hp6, hp5, 1)

        conj1 = AndConjunction(cond1, cond2)
        conj2 = OrConjunction(conj1, cond3)
        conj3 = AndConjunction(conj2, cond6, cond7)
        cs.add_condition(cond4)
        cs.add_condition(cond5)
        cs.add_condition(conj3)

        samples = []
        for i in range(5):
            cs.seed(1)
            samples.append([])
            for j in range(100):
                sample = cs.sample_configuration()
                samples[-1].append(sample)

            if i > 0:
                for j in range(100):
                    self.assertEqual(samples[-1][j], samples[-2][j])

    def test_sample_wrong_argument(self):
        cs = ConfigurationSpace()
        self.assertRaisesRegex(TypeError,
                               "Argument size must be of type int, but is "
                               "<class 'float'>", cs.sample_configuration, 1.2)
                               


class ConfigurationTest(unittest.TestCase):
    def setUp(self):
        cs = ConfigurationSpace()
        hp1 = cs.add_hyperparameter(CategoricalHyperparameter("parent", [0, 1]))
        hp2 = cs.add_hyperparameter(
            UniformIntegerHyperparameter("child", 0, 10))
        hp3 = cs.add_hyperparameter(
            UniformIntegerHyperparameter("friend", 0, 5))
        self.cs = cs

    def test_wrong_init(self):
        self.assertRaisesRegexp(ValueError,
                               'Configuration neither specified as dictionary '
                               'or vector.', Configuration, self.cs)

        self.assertRaisesRegexp(ValueError,
                               'Configuration specified both as dictionary and '
                               'vector, can only do one.', Configuration,
                               self.cs, values={}, vector=np.zeros((3, )))

    def test_init_with_values(self):
        c1 = Configuration(self.cs, values={'parent': 1,
                                            'child': 2,
                                            'friend': 3})
        # Pay attention that the vector does not necessarily has an intuitive
        #  sorting!
        # Values are a little bit higher than one would expect because,
        # an integer range of [0,10] is transformed to [-0.499,10.499].
        vector_values = {'parent': 1,
                         'child': 0.22727223140405708,
                         'friend': 0.583333611112037}
        vector = [None] * 3
        for name in self.cs._hyperparameter_idx:
            vector[self.cs._hyperparameter_idx[name]] = vector_values[name]
        c2 = Configuration(self.cs, vector=vector)
        # This tests
        # a) that the vector representation of both are the same
        # b) that the dictionary representation of both are the same
        self.assertEqual(c1, c2)

    def test_uniformfloat_transform(self):
        """This checks whether a value sampled through the configuration
        space (it does not happend when the variable is sampled alone) stays
        equal when it is serialized via JSON and the deserialized again."""

        cs = ConfigurationSpace()
        a = cs.add_hyperparameter(UniformFloatHyperparameter('a', -5, 10))
        b = cs.add_hyperparameter(NormalFloatHyperparameter('b', 1, 2,
                                                            log=True))
        for i in range(100):
            config = cs.sample_configuration()
            value = OrderedDict(sorted(config.get_dictionary().items()))
            string = json.dumps(value)
            saved_value = json.loads(string)
            saved_value = OrderedDict(sorted(byteify(saved_value).items()))
            self.assertEqual(repr(value), repr(saved_value))

        # Next, test whether the truncation also works when initializing the
        # Configuration with a dictionary
        for i in range(100):
            rs = np.random.RandomState(1)
            value_a = a.sample(rs)
            value_b = b.sample(rs)
            values_dict = {'a': value_a, 'b': value_b}
            config = Configuration(cs, values=values_dict)
            string = json.dumps(config.get_dictionary())
            saved_value = json.loads(string)
            saved_value = byteify(saved_value)
            self.assertEqual(values_dict, saved_value)
            
    def test_setitem(self):
        '''
        Checks overriding a sampled configuration
        '''
        pcs = ConfigurationSpace()
        pcs.add_hyperparameter(UniformIntegerHyperparameter('x0', 1, 5))
        pcs.add_hyperparameter(UniformFloatHyperparameter('x1', 0.5, 2.55))
        pcs.add_hyperparameter(CategoricalHyperparameter('x2',['ab', 'bc', 'cd', 'de']))
        
        conf = pcs.sample_configuration()
        
        # failed because it's a invalid configuration
        with self.assertRaisesRegex(ValueError, 'Illegal value 0 for hyperparameter x1'):
            conf['x1'] = 0
            
        with self.assertRaisesRegex(ValueError, 'Illegal value 2.5 for hyperparameter x0'):
            conf['x0'] = 2.5
        
        # failed because the variable didn't exists
        with self.assertRaisesRegex(KeyError, "Hyperparameter 'x_0' does not exist in this configuration space."):
            conf['x_0'] = 1
        
        # successful operation 1
        x1_old = conf['x1']
        if x1_old == 1.5:
            conf['x1'] = 2.1
        else:
            conf['x1'] = 1.5
        x1_new = conf['x1']
        self.assertNotEqual(x1_old, x1_new)
        
        # successful operation 2
        x2_old = conf['x2']
        if x2_old == 'ab':
            conf['x2'] = 'cd'
        else:
            conf['x2'] = 'ab'
        x2_new = conf['x2']
        self.assertNotEqual(x2_old, x2_new)
        





















