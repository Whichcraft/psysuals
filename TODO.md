# TODO

This document tracks bugs, memory leaks, performance bottlenecks, and other technical debt found during deep codebase inspection.

## 1. High Priority (Crashes & Compatibility Bugs)

## 2. Medium Priority (Resource Leaks & Performance)

## 3. Low Priority / Maintenance

- [x] **Persistence Effect with Real 3D Models**
  - **Description:** Add a persistence effect that uses actual 3D models, similar to the cube-style visual effect.
  - **Notes:** This should be implemented with proper model handling rather than a flat placeholder shape.

- [x] **Resolution Check on Effect Changes**
  - **Description:** Verify that the output resolution stays correct when switching effects, especially in `gl` mode.
  - **Notes:** Watch for resize or viewport mismatches during effect transitions.
