"""
Classes for caching metadata about a PerfDB instance.
"""

from lnt.viewer.PerfDB import Run, RunInfo, Test

class SuiteSummary:
    def __init__(self, name, path):
        self.name = name
        self.path = path

class PerfDBSummary:
    @staticmethod
    def fromdb(db):
        revision = db.get_revision_number("Run")

        # Look for all the run tags and use them to identify the available
        # suites.
        q = db.session.query(RunInfo.value.distinct())
        q = q.filter(RunInfo.key == "tag")

        suites = [SuiteSummary("Nightlytest", ("nightlytest",))]
        for tag, in q:
            if tag == 'nightlytest':
                continue
            suites.append(SuiteSummary(tag, ("simple",tag)))

        suites.sort(key=lambda s: s.name)
        return PerfDBSummary(revision, suites)

    def __init__(self, revision, suites):
        self.revision = revision
        self.suites = suites

    def is_up_to_date(self, db):
        return self.revision == db.get_revision_number("Run")

class SimpleSuiteSummary(object):
    @staticmethod
    def fromdb(db, tag):
        revision = db.get_revision_number("Test")

        # Find all test names.
        q = db.session.query(Test)
        q = q.filter(Test.name.startswith(tag))
        tests = list(q)

        # Collect all the test data.
        test_names = set()
        parameter_sets = set()
        test_map = {}
        has_status_markers = False
        has_success_markers = False
        for t in tests:
            name = t.name.split('.', 1)[1]

            items = [(k,v.value) for k,v in t.info.items()]
            items.sort()
            key = tuple(items)

            parameter_sets.add(key)
            test_map[(name, key)] = t

            if name.endswith('.success'):
                test_name = name.rsplit('.', 1)[0]
                has_success_markers = True
            elif name.endswith('.status'):
                test_name = name.rsplit('.', 1)[0]
                has_status_markers = True
            else:
                test_name = name

            test_names.add(test_name)

        # Compute the test status info.
        test_status_map = {}
        if has_status_markers:
            for test_name in test_names:
                marker_name = '%s.status' % test_name
                test_status_map[test_name] = (marker_name, True)
        elif has_success_markers:
            for test_name in test_names:
                marker_name = '%s.success' % test_name
                test_status_map[test_name] = (marker_name, False)

        # Order the test names.
        test_names = list(test_names)
        test_names.sort()

        # Collect the set of all parameter keys.
        parameter_keys = list(set([k for pset in parameter_sets
                                   for k,v in pset]))
        parameter_keys.sort()

        # Order the parameter sets and convert to dictionaries.
        parameter_sets = list(parameter_sets)
        parameter_sets.sort()

        return SimpleSuiteSummary(revision, tag, test_names,
                                  test_map, test_status_map,
                                  parameter_keys, parameter_sets)

    def __init__(self, revision, tag, test_names,
                 test_map, test_status_map,
                 parameter_keys, parameter_sets):
        self.revision = revision
        self.tag = tag
        self.test_names = test_names
        self.test_map = test_map
        self.test_status_map = test_status_map
        self.parameter_keys = parameter_keys
        self.parameter_sets = parameter_sets

    def is_up_to_date(self, db):
        return self.revision == db.get_revision_number("Test")

_cache = {}
def get_simple_suite_summary(db, tag):
    key = (db.path, tag)
    entry = _cache.get(key)
    if entry is None or not entry.is_up_to_date(db):
        _cache[key] = entry = SimpleSuiteSummary.fromdb(db, tag)
    return entry

class SimpleSuiteRunSummary(object):
    _cache = {}
    @staticmethod
    def get_summary(db, tag):
        key = (db.path, tag)
        entry = SimpleSuiteRunSummary._cache.get(key)
        if entry is None or not entry.is_up_to_date(db):
            entry = SimpleSuiteRunSummary.fromdb(db, tag)
            SimpleSuiteRunSummary._cache[key] = entry
        return entry

    @staticmethod
    def fromdb(db, tag):
        revision = db.get_revision_number("RunInfo")

        # Find all run_orders for runs with this tag.
        all_run_orders = db.session.query(RunInfo.value, RunInfo.run_id,
                                          Run.machine_id).\
            join(Run).\
            filter(RunInfo.key == "run_order").\
            filter(RunInfo.run_id.in_(
                db.session.query(RunInfo.run_id).\
                    filter(RunInfo.key == "tag").\
                    filter(RunInfo.value == tag).subquery()))
        order_by_run = dict((run_id,order)
                            for order,run_id,machine_id in all_run_orders)
        machine_id_by_run = dict((run_id,machine_id)
                                 for order,run_id,machine_id in all_run_orders)

        # Create a mapping from run_order to the available runs with that order.
        runs_by_order = {}
        for order,run_id,_ in all_run_orders:
            runs = runs_by_order.get(order)
            if runs is None:
                runs = runs_by_order[order] = []
            runs.append(run_id)

        # Get all available run_orders, in order.
        def order_key(run_order):
            return run_order
        run_orders = runs_by_order.keys()
        run_orders.sort(key = order_key)
        run_orders.reverse()

        # Construct the total order of runs.
        runs_in_order = []
        for order in run_orders:
            runs_in_order.extend(runs_by_order[order])

        return SimpleSuiteRunSummary(
            revision, tag, run_orders, runs_by_order, runs_in_order,
            order_by_run, machine_id_by_run)

    def __init__(self, revision, tag, run_orders, runs_by_order, runs_in_order,
                 order_by_run, machine_id_by_run):
        self.revision = revision
        self.tag = tag
        self.run_orders = run_orders
        self.runs_by_order = runs_by_order
        self.runs_in_order = runs_in_order
        self.order_by_run = order_by_run
        self.machine_id_by_run = machine_id_by_run

    def is_up_to_date(self, db):
        return self.revision == db.get_revision_number("RunInfo")

    def get_run_order(self, run_id):
        return self.order_by_run.get(run_id)

    def get_run_ordered_index(self, run_id):
        try:
            return self.runs_in_order.index(run_id)
        except:
            print run_id
            print self.runs_in_order
            raise

    def get_previous_run_on_machine(self, run_id):
        machine_id = self.machine_id_by_run[run_id]
        index = self.get_run_ordered_index(run_id)
        for i in range(index + 1, len(self.runs_in_order)):
            id = self.runs_in_order[i]
            if machine_id == self.machine_id_by_run[id]:
                return id

    def get_next_run_on_machine(self, run_id):
        machine_id = self.machine_id_by_run[run_id]
        index = self.get_run_ordered_index(run_id)
        for i in range(0, index)[::-1]:
            id = self.runs_in_order[i]
            if machine_id == self.machine_id_by_run[id]:
                return id