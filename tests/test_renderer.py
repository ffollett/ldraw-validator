import pytest
import os
import shutil
from unittest.mock import patch, MagicMock
from validator.scene_graph import SceneGraph
from validator.parser import Placement
from validator.renderer import render_scene

class TestRendererUnits:
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_render_scene_command_generation(self, mock_which, mock_subprocess):
        # Setup
        def which_side_effect(arg):
            if arg == "LDView": return "LDView"
            return None
            
        mock_which.side_effect = which_side_effect
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        sg = SceneGraph()
        p1 = Placement("3001", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1))
        sg.add_placement(p1)
        
        output_path = "test_render.png"
        
        # Execute
        success = render_scene(sg, output_path, width=320, height=240)
        
        # Verify
        assert success is True
        
        # Check arguments used to call LDView
        args, kwargs = mock_subprocess.call_args
        cmd_list = args[0]
        
        assert cmd_list[0] == "LDView"
        assert any(arg.startswith("-SaveSnapshot=") for arg in cmd_list)
        assert "-SaveWidth=320" in cmd_list
        assert "-SaveHeight=240" in cmd_list
        
        # Verify tmp file was cleaned up? 
        # The function uses tempfile with delete=False but calls os.unlink.
        # We can't easily check file existence since it was deleted, 
        # but we can check if it passed a file path.
        ldr_file = cmd_list[1]
        assert ldr_file.endswith(".ldr")

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_render_failure_handling(self, mock_which, mock_subprocess):
        mock_which.return_value = "LDView"
        # Simulate failure
        mock_subprocess.side_effect = Exception("LDView crashed")
        
        sg = SceneGraph()
        success = False
        try:
             success = render_scene(sg, "out.png")
        except:
             pass
             
        # Our code catches Known errors? 
        # It specifically catches subprocess.CalledProcessError.
        # Exception might bubble up.
        
