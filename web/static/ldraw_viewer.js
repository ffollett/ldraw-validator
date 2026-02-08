/**
 * LDraw 3D Viewer using Three.js
 * Renders LDraw parts in an interactive 3D view
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { LDrawLoader } from 'three/addons/loaders/LDrawLoader.js';

class LDrawViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container ${containerId} not found`);
        }

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.currentModel = null;
        this.animationId = null;

        this.init();
    }

    init() {
        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);

        // Create camera
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(45, width / height, 1, 10000);
        this.camera.position.set(200, 200, 200);

        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Add orbit controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;

        // Add lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.5);
        directionalLight1.position.set(1, 1, 1);
        this.scene.add(directionalLight1);

        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
        directionalLight2.position.set(-1, -1, -1);
        this.scene.add(directionalLight2);

        // Start animation loop
        this.animate();

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    async loadPart(partId) {
        try {
            // Show loading state
            this.showLoading(true);

            // Fetch LDraw file content
            const response = await fetch(`/api/parts/${partId}/ldraw`);
            if (!response.ok) {
                throw new Error(`Failed to load part: ${response.statusText}`);
            }

            const ldrawContent = await response.text();

            // Clear existing model
            this.clear();

            // Parse and load LDraw content
            const loader = new LDrawLoader();

            // Set library paths for sub-parts and primitives
            loader.setPartsLibraryPath('/');

            // Enable smooth normals for better rendering
            loader.smoothNormals = true;

            try {
                // Preload materials from LDConfig.ldr to fix colors (brown/purple issue)
                await loader.preloadMaterials('LDConfig.ldr');
            } catch (err) {
                console.warn('Failed to preload LDConfig.ldr, falling back to default colors', err);
            }

            return new Promise((resolve) => {
                // parse(text, onLoad) only takes TWO arguments in Three.js v0.160.0 LDrawLoader
                loader.parse(
                    ldrawContent,
                    (group) => {
                        // LDraw uses Y-down coordinate system, Three.js uses Y-up
                        // Rotate 180° around X-axis to flip the model right-side up
                        group.rotation.x = Math.PI;

                        this.currentModel = group;
                        this.scene.add(group);

                        // Center and scale the model
                        this.fitCameraToModel(group);

                        this.showLoading(false);
                        resolve(group);
                    }
                );
            });
        } catch (error) {
            this.showLoading(false);
            this.showError(error.message);
            throw error;
        }
    }

    async loadFromContent(ldrawContent, filename = "model.ldr") {
        try {
            this.showLoading(true);

            // Clear existing model
            this.clear();

            // Parse and load LDraw content
            const loader = new LDrawLoader();
            loader.setPartsLibraryPath('/');
            loader.smoothNormals = true;

            try {
                await loader.preloadMaterials('LDConfig.ldr');
            } catch (err) {
                console.warn('Failed to preload LDConfig.ldr', err);
            }

            return new Promise((resolve) => {
                loader.parse(
                    ldrawContent,
                    (group) => {
                        group.rotation.x = Math.PI;
                        this.currentModel = group;
                        this.scene.add(group);
                        this.fitCameraToModel(group);
                        this.showLoading(false);
                        resolve(group);
                    }
                );
            });
        } catch (error) {
            this.showLoading(false);
            this.showError(error.message);
            throw error;
        }
    }

    fitCameraToModel(model) {
        // Calculate bounding box
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        // Calculate distance to fit the model
        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.fov * (Math.PI / 180);
        let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
        cameraZ *= 1.5; // Add some padding

        // Position camera to match 2D render viewpoint (front-top-right angle)
        // LDraw standard view is from above and slightly to the front-right
        const offset = cameraZ * 0.7;
        this.camera.position.set(
            center.x + offset,      // Right
            center.y + offset,      // Above
            center.z + offset * 1.5 // Front
        );
        this.camera.lookAt(center);

        // Update controls target
        this.controls.target.copy(center);
        this.controls.update();
    }

    clear() {
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
            this.currentModel.traverse((child) => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach(m => m.dispose());
                    } else {
                        child.material.dispose();
                    }
                }
            });
            this.currentModel = null;
        }

        // Clear loading/error messages
        const existingMessages = this.container.querySelectorAll('.viewer-message');
        existingMessages.forEach(msg => msg.remove());
    }

    showLoading(show) {
        const existingLoader = this.container.querySelector('.viewer-loading');
        if (show) {
            if (!existingLoader) {
                const loader = document.createElement('div');
                loader.className = 'viewer-loading viewer-message';
                loader.innerHTML = '<div class="spinner"></div><p>Loading 3D model...</p>';
                this.container.appendChild(loader);
            }
        } else {
            if (existingLoader) {
                existingLoader.remove();
            }
        }
    }

    showError(message) {
        const error = document.createElement('div');
        error.className = 'viewer-error viewer-message';
        error.innerHTML = `<p>❌ Error: ${message}</p>`;
        this.container.appendChild(error);
    }

    dispose() {
        // Stop animation
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }

        // Clean up model
        this.clear();

        // Clean up renderer
        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }

        // Clean up controls
        if (this.controls) {
            this.controls.dispose();
        }

        // Remove resize listener
        window.removeEventListener('resize', () => this.onWindowResize());
    }
}

// Export for use in other modules
export { LDrawViewer };

// Also make available globally for inline scripts
window.LDrawViewer = LDrawViewer;
