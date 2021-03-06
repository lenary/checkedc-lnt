# RUN: lnt profile getVersion %S/Inputs/test.lntprof | FileCheck --check-prefix=CHECK-GETVERSION %s
# CHECK-GETVERSION: 1

# RUN: lnt profile getTopLevelCounters %S/Inputs/test.lntprof | FileCheck --check-prefix=CHECK-GETTLC %s
# CHECK-GETTLC: {"cycles": 12345.0, "branch-misses": 200.0}

# RUN: lnt profile getFunctions %S/Inputs/test.lntprof | FileCheck --check-prefix=CHECK-GETFUNCTIONS %s
# CHECK-GETFUNCTIONS: {"fn1": {"length": 2, "counters": {"cycles": 45.0, "branch-misses": 10.0}}}

# RUN: lnt profile getCodeForFunction %S/Inputs/test.lntprof fn1 | FileCheck --check-prefix=CHECK-GETFN1 %s
# CHECK-GETFN1: [{}, 1048576, "add r0, r0, r0"], [{"cycles": 100.0}, 1048580, "sub r1, r0, r0"]]
