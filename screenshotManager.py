import io 
import base64
import sys
import json 
from typing import Dict, Any, Optional, List
from PIL import Image

try:
    import mss
    _HAS_MSS = True
except ImportError:
    _HAS_MSS = False

class ScreenshotManager:
    def __init__(self, quality: int=65, max_width: int=1600):
        self.quality = max(30, min(95, quality))
        self.max_width = max_width
        self.platform = sys.platform
        self.check_platform()
        self.displays = self._detect_displays()

    def check_platform(self):
        if not (self.platform.startswith('win') or self.platform.startswith('linux')):
            raise RuntimeError(f"Unsupported platform: {self.platform}")

    def _detect_displays(self) -> List[Dict]:
        """Détecte tous les écrans"""
        if not _HAS_MSS:
            return []
        try:
            with mss.mss() as sct:
                return sct.monitors[1:]  # Ignore virtuel
        except:
            return []

    def capture_mss(self)-> Optional[List[Dict]]:
        try:
            if not _HAS_MSS:
                return None
            
            with mss.mss() as sct:
                monitors = []
                for monitor_id, monitor in enumerate(self._detect_displays(), 1):
                    try:
                        screenshot = sct.grab(monitor)
                        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                        monitors.append({
                            'id': monitor_id,
                            'image': img,
                            'width': screenshot.width,
                            'height': screenshot.height
                        })
                    except:
                        continue
                return monitors if monitors else None
        except:
            return None

    def capture_windows_native(self)->Optional[List[Dict]]:
        try:
            import win32gui
            import win32ui
            import win32con
            import win32api
            
            hdesktop = win32gui.GetDesktopWindow()
            left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
            width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            
            desktop_dc = win32gui.GetWindowDC(hdesktop)
            img_dc = win32ui.CreateDCFromHandle(desktop_dc)
            mem_dc = img_dc.CreateCompatibleDC()
            
            screenshot = win32ui.CreateBitmap()
            screenshot.CreateCompatibleBitmap(img_dc, width, height)
            mem_dc.SelectObject(screenshot)
            mem_dc.BitBlt((0, 0), (width, height), img_dc, (left, top), win32con.SRCCOPY)
            
            bmpinfo = screenshot.GetInfo()
            bmpstr = screenshot.GetBitmapBits(True)
            img = Image.frombytes(
                'RGB', 
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']), 
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Cleanup
            mem_dc.DeleteDC()
            win32gui.DeleteObject(screenshot.GetHandle())
            win32gui.ReleaseDC(hdesktop, desktop_dc)
            
            return [{
                'id': 1, 
                'image': img, 
                'width': img.width, 
                'height': img.height
            }]
        except:
            return None
        
    def capture_linux_fallback(self)-> Optional[List[Dict]]:
        try:
            from PIL import ImageGrab
            
            img = ImageGrab.grab()
            return [{
                'id': 1,
                'image': img,
                'width': img.width,
                'height': img.height
            }]
            
        except Exception:
            try:
                import subprocess
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    temp_path = tmp.name
                    try:
                        subprocess.run(
                            ['scrot', temp_path],
                            check=True,
                            timeout=10,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        img = Image.open(temp_path)
                        result = [{
                            'id': 1, 
                            'image': img, 
                            'width': img.width, 
                            'height': img.height
                        }]
                    finally:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                    return result
            except Exception:
                return None
            
    def optimize_image(self, image: Image.Image) -> Image.Image:
        if image.width > self.max_width:
            ratio = self.max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
            
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return image
        
    def image_to_base64(self, image: Image.Image)-> Dict[str, Any]:
        try:
            buffer = io.BytesIO()
            image.save(buffer, 'JPEG', quality=self.quality, optimize=True)
            buffer.seek(0)
            
            image_data = base64.b64encode(buffer.getvalue()).decode('ascii')
            size_kb = (len(image_data)*3)//4//1024
            return {
                'success': True,
                'data': image_data,
                'width': image.width,
                'height': image.height,
                'size_kb': size_kb,
                'quality': self.quality
            }
        except Exception as e:
            return {'success': False, "error": str(e)}
        
    def capture_single(self)-> Dict[str, Any]:
        try:
            screens = None
            
            if self.platform.startswith('win'):
                screens = self.capture_mss() or self.capture_windows_native()
            else:
                screens = self.capture_mss() or self.capture_linux_fallback()
            
            if screens and len(screens) > 0:
                screen = screens[0]
                optimized_img = self.optimize_image(screen['image'])
                return self.image_to_base64(optimized_img)
            else:
                return {
                    'success': False,
                    'error': 'All capture methods failed'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
    def capture_multiple(self)-> Dict[str, Any]:
        try:
            screens = None
            
            if self.platform.startswith('win'):
                screens = self.capture_mss() or self.capture_windows_native()
            else:
                screens = self.capture_mss() or self.capture_linux_fallback()
            
            if not screens:
                single_result = self.capture_single()
                if single_result['success']:
                    return {
                        'success': True,
                        'displays': 1,
                        'results': [single_result]
                    }
                else:
                    return {'success': False, 'error': 'Multi-capture failed'}
                
            results = []
            for screen in screens:
                optimized_img = self.optimize_image(screen['image'])
                result = self.image_to_base64(optimized_img)
                if result['success']:
                    result['display_id'] = screen['id']
                    results.append(result)
            
            return {
                'success': True,
                'displays': len(results),
                'results': results
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
    def update_config(self, quality:int=None, max_width:int = None)-> Dict[str, Any]:
        if quality is not None:
            self.quality = max(30, min(95, quality))
        if max_width is not None:
            self.max_width = max_width
        
        return {
            'quality': self.quality,
            'max_width': self.max_width
        }

_screenshot_manager = None

def get_screenshot_manager(quality=65, max_width=1600):
    global _screenshot_manager
    if _screenshot_manager is None:
        _screenshot_manager = ScreenshotManager(quality=quality, max_width=max_width)
    return _screenshot_manager

def take_screenshot(quality=65, multi_display=False):
    manager = get_screenshot_manager(quality)
    if multi_display:
        return manager.capture_multiple()
    else:
        return manager.capture_single()