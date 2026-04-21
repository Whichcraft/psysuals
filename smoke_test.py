#!/usr/bin/env python3
import sys
import pygame
import os

# Mock display for headless testing
os.environ['SDL_VIDEODRIVER'] = 'dummy'

def test_imports():
    print("Checking imports...")
    try:
        import psysualizer
        import config
        from effects import MODES
        print("✅ Core imports OK")
        return MODES
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

def test_effects(MODES):
    print(f"Checking {len(MODES)} effects...")
    import config
    config.WIDTH = 800
    config.HEIGHT = 600
    
    pygame.init()
    pygame.display.set_mode((1, 1))
    
    passed = 0
    failed = 0
    for name, VisCls in MODES:
        try:
            vis = VisCls()
            print(f"  ✅ {name:12} instantiated")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name:12} FAILED: {e}")
            failed += 1
            
    print(f"\nResults: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)

def run_smoke_tests():
    modes = test_imports()
    test_effects(modes)
    
    print("\nRunning regression checks...")
    from core.regression_tester import test_registry_order, test_all_effects_inherit_base, test_all_files_registered
    test_registry_order()
    test_all_effects_inherit_base()
    test_all_files_registered()
    
    print("\n✅ All smoke and regression tests PASSED")

if __name__ == "__main__":
    run_smoke_tests()
