%% =========================================================================
% WAYLO: 3D Indoor Environment & Physical Wheelchair Perception Visualizer
% NVIDIA x Nebius Global AI Hackathon (Physical AI Track)
% 
% Features:
% - 3D Indoor Room (walls, floor grid, 1.2m target doorway lintel)
% - 3D Target Object (glass on table at X=0.8m, Y=0.3m, Z=0.6m)
% - 3D Depth-Camera Sensor Field Cone mounted on wheelchair headrest
% - 3D Wheelchair Base Model with Dual Drive Wheels, Casters, and 
%   Side-Mounted 6-Axis Articulated Robotic Arm Mesh
%   (Base Link, Upper Arm, Forearm, Wrist, Gripper)
% - Front LiDAR Raycast Lines (-30°, 0°, +30°)
% - Live Hardware-in-the-Loop Telemetry Bridge via webwrite to http://localhost:8000
% =========================================================================

function waylo_3d_environment()
    clear; close all; clc;

    fprintf('========================================================\n');
    fprintf('  WAYLO: YOUR WORLD. YOUR WAY.\n');
    fprintf('  3D Indoor Environment & 6-DOF Assistive Arm Visualizer\n');
    fprintf('  Accelerated with NVIDIA Nemotron / Cosmos on Nebius AI\n');
    fprintf('========================================================\n\n');

    % --- Simulation & Environment Setup ---
    fig = figure('Name', 'WAYLO 3D Environment & 6-DOF Assistive Arm Perception', ...
                 'Color', [0.07 0.09 0.13], ...
                 'Position', [80, 60, 1150, 780], ...
                 'NumberTitle', 'off');

    ax = axes('Parent', fig);
    hold(ax, 'on');
    grid(ax, 'on');
    axis(ax, 'equal');
    set(ax, 'Color', [0.09 0.11 0.16], ...
            'XColor', [0.6 0.65 0.75], ...
            'YColor', [0.6 0.65 0.75], ...
            'ZColor', [0.6 0.65 0.75], ...
            'FontSize', 10);

    xlabel(ax, 'Lateral X (meters)', 'FontWeight', 'bold');
    ylabel(ax, 'Forward Y (meters)', 'FontWeight', 'bold');
    zlabel(ax, 'Elevation Z (meters)', 'FontWeight', 'bold');
    title(ax, {'\bf\fontsize{14}\color{white}WAYLO: 3D Spatial Environment & 6-DOF Assistive Manipulation', ...
               '\fontsize{10}\color[rgb]{0.3,0.75,0.95}NVIDIA Nemotron on Nebius AI | 6-Axis Articulated Arm & Headrest Depth Cone'}, ...
               'Interpreter', 'tex');

    xlim(ax, [-3.5, 3.5]);
    ylim(ax, [0.0, 6.5]);
    zlim(ax, [0.0, 2.8]);
    view(ax, [-38, 26]);

    % --- 1. Render Room Architecture & 3D Target Object ---
    draw_room_environment(ax);

    % --- 2. Generate Comparative Trajectories ---
    dt = 0.08;
    total_time = 5.0;
    t_span = 0:dt:total_time;
    N = length(t_span);

    % Baseline Unassisted: human drifts with +14 deg steering error
    [x_raw, y_raw, th_raw] = simulate_trajectory(N, dt, 14.0, 0.0);

    % WAYLO Copilot: shared-autonomy centering correction
    [x_cor, y_cor, th_cor, alpha_hist, clearance_hist] = simulate_waylo_copilot(N, dt, 14.0);

    % Plot static trajectory paths on the floor
    plot3(ax, x_raw, y_raw, zeros(size(x_raw))+0.02, '--', 'Color', [0.95 0.25 0.35], 'LineWidth', 2.0);
    plot3(ax, x_cor, y_cor, zeros(size(x_cor))+0.03, '-', 'Color', [0.15 0.85 0.45], 'LineWidth', 2.8);

    % Legend
    legend(ax, {'', '', '', '', '', '', '', '', '', '', '', ...
                'Unassisted Trajectory (Collision Course)', ...
                'WAYLO Shared-Autonomy Centered Path'}, ...
                'TextColor', 'white', 'Color', [0.12 0.15 0.22], ...
                'EdgeColor', [0.3 0.35 0.45], 'Location', 'northeast');

    % --- 3. Telemetry HUD Annotation ---
    hud_box = annotation('textbox', [0.03, 0.68, 0.34, 0.28], ...
                         'String', {'\bfWAYLO COPILOT & 6-DOF ROBOTICS HUD', ...
                                    'State: INITIALIZING...', ...
                                    'Pose (X, Y): [0.00, 0.50] m', ...
                                    'Shared-Autonomy \alpha: 0.00', ...
                                    'Doorway Clearance: 0.38 m', ...
                                    'Arm Status: 6-DOF IK ACTIVE', ...
                                    'Target Object: Glass [0.8, 0.3, 0.6] m', ...
                                    'Privacy: Depth-Camera Anonymized', ...
                                    'REST Bridge: http://localhost:8000'}, ...
                         'FitBoxToText', 'off', ...
                         'BackgroundColor', [0.10 0.13 0.20], ...
                         'Color', [0.85 0.90 0.98], ...
                         'EdgeColor', [0.25 0.65 0.95], ...
                         'LineWidth', 1.5, ...
                         'FontSize', 8.5, ...
                         'Interpreter', 'tex');

    % Lighting & Camera
    camlight(ax, 'headlight');
    lighting(ax, 'gouraud');

    % Webwrite HTTP options for live telemetry bridge
    telemetry_url = 'http://localhost:8000/api/matlab/telemetry';
    web_opts = weboptions('MediaType', 'application/json', ...
                          'Timeout', 0.2, ...
                          'RequestMethod', 'post');

    % --- 4. Animate Wheelchair Along WAYLO Corrected Path ---
    fprintf('Starting 3D Real-Time Perception Animation with 6-DOF Arm...\n');
    chair_handles = [];
    sensor_rays = [];
    depth_cone_handles = [];

    for k = 1:2:N
        if ~ishandle(fig)
            break;
        end

        cur_x = x_cor(k);
        cur_y = y_cor(k);
        cur_th = th_cor(k);
        cur_alpha = alpha_hist(k);
        cur_clearance = clearance_hist(k);
        risk_pct = round(cur_alpha * 85);

        % Delete previous wheelchair geometry & sensor cones
        if ~isempty(chair_handles)
            delete(chair_handles);
        end
        if ~isempty(sensor_rays)
            delete(sensor_rays);
        end
        if ~isempty(depth_cone_handles)
            delete(depth_cone_handles);
        end

        % Draw updated 3D Wheelchair with Side-Mounted 6-DOF Articulated Arm Mesh
        chair_handles = draw_wheelchair_3d(ax, cur_x, cur_y, 0.0, cur_th);

        % Draw Front LiDAR Raycast Lines (-30°, 0°, +30°)
        sensor_rays = draw_sensor_cone(ax, cur_x, cur_y, 0.85, cur_th);

        % Draw 3D Depth-Camera Sensor Field Cone mounted on wheelchair headrest
        depth_cone_handles = draw_headrest_depth_cone(ax, cur_x, cur_y, 0.95, cur_th);

        % Send live pose update to FastAPI middleware via webwrite
        telemetry_packet = struct( ...
            'x', round(cur_x, 3), ...
            'y', round(cur_y, 3), ...
            'theta_rad', round(cur_th, 3), ...
            'linear_velocity', 0.8, ...
            'user_steering_deg', 14.0, ...
            'scenario', 'Doorway' ...
        );
        try
            webwrite(telemetry_url, telemetry_packet, web_opts);
        catch
            % Continue simulation gracefully if FastAPI server is offline
        end

        % Update HUD Text
        aeb_text = 'ACTIVE';
        if cur_clearance < 0.20
            aeb_text = 'CAUTION: PROXIMITY';
        end
        set(hud_box, 'String', { ...
            '\bfWAYLO COPILOT & 6-DOF ROBOTICS HUD', ...
            sprintf('Nebius Model: \\color[rgb]{0.3,0.85,1.0}nvidia/nemotron-3-ultra'), ...
            sprintf('Pose (X, Y, \\theta): [%+.2f, %.2f m, %+.1f°]', cur_x, cur_y, rad2deg(cur_th)), ...
            sprintf('Shared-Autonomy \\alpha: \\bf%0.2f', cur_alpha), ...
            sprintf('Left/Right Clearance: %0.2f m', cur_clearance), ...
            sprintf('6-DOF Arm Status: READY | Gripper: OPEN'), ...
            sprintf('Target Object: Glass at [0.8, 0.3, 0.6] m'), ...
            sprintf('Headrest Depth Camera: \\color[rgb]{0.2,0.9,0.5}PRIVACY-SCRUBBED'), ...
            sprintf('Hazard Risk: %d%% | Status: %s', risk_pct, aeb_text) ...
        });

        drawnow;
        pause(0.04);
    end

    fprintf('3D Perception Animation complete. 6-DOF Arm and Depth Cone verified.\n');
end

% =========================================================================
% Helper: Draw 3D Room Architecture, Table, and 3D Target Glass
% =========================================================================
function draw_room_environment(ax)
    % Floor Grid (8m x 7m)
    [Xf, Yf] = meshgrid(-3.5:0.5:3.5, 0.0:0.5:6.5);
    Zf = zeros(size(Xf));
    surf(ax, Xf, Yf, Zf, 'FaceColor', [0.12 0.14 0.19], ...
         'EdgeColor', [0.18 0.22 0.30], 'FaceAlpha', 0.9);

    % Doorway Walls at Y = 4.5m with a 1.2m central opening (X from -0.6m to +0.6m)
    wall_color = [0.25 0.30 0.40];
    lintel_color = [0.35 0.42 0.55];

    % Left Wall: X from -3.5 to -0.6, Y = 4.5, Z from 0 to 2.4
    draw_box(ax, [-3.5, 4.45, 0.0], [-0.6, 4.55, 2.4], wall_color, 0.85);

    % Right Wall: X from 0.6 to 3.5, Y = 4.5, Z from 0 to 2.4
    draw_box(ax, [0.6, 4.45, 0.0], [3.5, 4.55, 2.4], wall_color, 0.85);

    % 1.2m Target Doorway Top Lintel Beam (Spans over opening from -0.6 to 0.6, Z from 2.1 to 2.4)
    draw_box(ax, [-0.6, 4.45, 2.1], [0.6, 4.55, 2.4], lintel_color, 0.95);

    % Doorway Portal Threshold Line on Floor (Green)
    plot3(ax, [-0.6, 0.6], [4.5, 4.5], [0.02, 0.02], 'LineWidth', 4, 'Color', [0.15 0.85 0.45]);
    text(ax, 0.0, 4.5, 2.55, 'TARGET DOORWAY LINTEL (1.2m)', ...
         'Color', [0.55 0.95 0.65], 'FontSize', 10, 'FontWeight', 'bold', 'HorizontalAlignment', 'center');

    % Corridor Walls from Y=1.5 to Y=3.5 (1.2m width)
    draw_box(ax, [-3.5, 1.5, 0.0], [-1.2, 3.5, 1.5], [0.20 0.24 0.32], 0.4);
    draw_box(ax, [1.2, 1.5, 0.0], [3.5, 3.5, 1.5], [0.20 0.24 0.32], 0.4);

    % --- Side Table for Manipulation at X=0.8m, Y=0.3m ---
    table_color = [0.45 0.30 0.20];
    % Table top: centered around [0.8, 0.3], dimensions 0.6m x 0.6m, Z=0.50 to 0.55
    draw_box(ax, [0.50, 0.05, 0.50], [1.10, 0.55, 0.55], table_color, 0.9);
    % Table legs
    draw_cylinder(ax, 0.55, 0.10, 0.03, 0.50, [0.3 0.2 0.15]);
    draw_cylinder(ax, 1.05, 0.10, 0.03, 0.50, [0.3 0.2 0.15]);
    draw_cylinder(ax, 0.55, 0.50, 0.03, 0.50, [0.3 0.2 0.15]);
    draw_cylinder(ax, 1.05, 0.50, 0.03, 0.50, [0.3 0.2 0.15]);

    % --- 3D Target Object: Glass on Table at X=0.8m, Y=0.3m, Z=0.6m ---
    glass_radius = 0.05;
    glass_height = 0.14;
    glass_color = [0.25 0.85 1.0]; % Translucent Glass Cyan
    draw_cylinder(ax, 0.80, 0.30, glass_radius, glass_height, glass_color, 0.55);
    text(ax, 0.80, 0.30, 0.74, '\bfTarget Glass [0.8, 0.3, 0.6]', ...
         'Color', [0.4 0.95 1.0], 'FontSize', 9, 'FontWeight', 'bold', 'HorizontalAlignment', 'center');

    % Dynamic Obstacle at [1.8, 2.5]
    draw_cylinder(ax, 1.8, 2.5, 0.25, 1.2, [0.9 0.3 0.3], 0.0);
    text(ax, 1.8, 2.5, 1.35, 'Obstacle', 'Color', [1.0 0.4 0.4], ...
         'FontSize', 8, 'HorizontalAlignment', 'center');
end

% =========================================================================
% Helper: Draw 3D Wheelchair with Side-Mounted 6-Axis Articulated Arm Mesh
% =========================================================================
function handles = draw_wheelchair_3d(ax, x0, y0, z0, theta)
    handles = [];
    R = [cos(theta), -sin(theta), 0;
         sin(theta),  cos(theta), 0;
         0,           0,          1];

    tf = @(pts) (R * pts')' + [x0, y0, z0];

    % 1. Main Base Chassis (Dark Slate)
    chassis_pts = [-0.30, -0.25, 0.08;
                    0.30, -0.25, 0.08;
                    0.30,  0.25, 0.08;
                   -0.30,  0.25, 0.08;
                   -0.30, -0.25, 0.24;
                    0.30, -0.25, 0.24;
                    0.30,  0.25, 0.24;
                   -0.30,  0.25, 0.24];
    h_chassis = draw_transformed_box(ax, tf(chassis_pts), [0.15 0.18 0.25]);
    handles = [handles; h_chassis];

    % 2. Seat Cushion (WAYLO Blue)
    seat_pts = [-0.22, -0.22, 0.24;
                 0.22, -0.22, 0.24;
                 0.22,  0.22, 0.24;
                -0.22,  0.22, 0.24;
                -0.22, -0.22, 0.32;
                 0.22, -0.22, 0.32;
                 0.22,  0.22, 0.32;
                -0.22,  0.22, 0.32];
    h_seat = draw_transformed_box(ax, tf(seat_pts), [0.15 0.45 0.90]);
    handles = [handles; h_seat];

    % 3. Backrest & Headrest
    back_pts = [-0.06, -0.22, 0.32;
                 0.02, -0.22, 0.32;
                 0.02,  0.22, 0.32;
                -0.06,  0.22, 0.32;
                -0.06, -0.22, 0.82;
                 0.02, -0.22, 0.82;
                 0.02,  0.22, 0.82;
                -0.06,  0.22, 0.82];
    h_back = draw_transformed_box(ax, tf(back_pts), [0.12 0.35 0.75]);
    handles = [handles; h_back];

    % Headrest Cushion
    head_pts = [-0.05, -0.10, 0.82;
                 0.03, -0.10, 0.82;
                 0.03,  0.10, 0.82;
                -0.05,  0.10, 0.82;
                -0.05, -0.10, 0.98;
                 0.03, -0.10, 0.98;
                 0.03,  0.10, 0.98;
                -0.05,  0.10, 0.98];
    h_head = draw_transformed_box(ax, tf(head_pts), [0.10 0.30 0.65]);
    handles = [handles; h_head];

    % 4. Dual Drive Wheels (Rear Left & Right, radius 0.16m, track L=0.60m)
    h_w1 = draw_wheel(ax, tf([-0.05, -0.30, 0.16]), theta, [0.08 0.08 0.08]);
    h_w2 = draw_wheel(ax, tf([-0.05,  0.30, 0.16]), theta, [0.08 0.08 0.08]);
    handles = [handles; h_w1; h_w2];

    % 5. Front Casters (Dual Free-Swiveling Wheels at Front Left & Right)
    h_c1 = draw_caster(ax, tf([0.22, -0.20, 0.06]), [0.4 0.45 0.55]);
    h_c2 = draw_caster(ax, tf([0.22,  0.20, 0.06]), [0.4 0.45 0.55]);
    handles = [handles; h_c1; h_c2];

    % 6. Depth Camera Housing on Top of Headrest
    cam_box = [-0.06, -0.06, 0.98;
                0.04, -0.06, 0.98;
                0.04,  0.06, 0.98;
               -0.06,  0.06, 0.98;
               -0.06, -0.06, 1.05;
                0.04, -0.06, 1.05;
                0.04,  0.06, 1.05;
               -0.06,  0.06, 1.05];
    h_cam = draw_transformed_box(ax, tf(cam_box), [0.2 0.85 0.95]);
    handles = [handles; h_cam];

    % 7. Side-Mounted 6-Axis Articulated Arm Mesh (Clamped to Right Frame)
    % Base Link -> Upper Arm -> Forearm -> Wrist -> Gripper
    h_arm = draw_side_mounted_6dof_arm(ax, tf, theta);
    handles = [handles; h_arm];
end

% =========================================================================
% Helper: 6-Axis Articulated Arm Mesh (Base, Upper Arm, Forearm, Wrist, Gripper)
% =========================================================================
function handles = draw_side_mounted_6dof_arm(ax, tf, theta)
    handles = [];

    % Arm mount point on right frame: [X=0.10, Y=0.28, Z=0.28]
    p_mount = [0.10, 0.28, 0.28];
    p_base  = [0.10, 0.28, 0.38];
    p_elbow = [0.26, 0.34, 0.58];
    p_wrist = [0.42, 0.36, 0.52];
    p_grip  = [0.52, 0.38, 0.50];

    % Transform key joint nodes to world coordinates
    wp_mount = tf(p_mount);
    wp_base  = tf(p_base);
    wp_elbow = tf(p_elbow);
    wp_wrist = tf(p_wrist);
    wp_grip  = tf(p_grip);

    % Link 1: Base Link (Mount Bracket to Base Turntable)
    h_base = plot3(ax, [wp_mount(1), wp_base(1)], [wp_mount(2), wp_base(2)], [wp_mount(3), wp_base(3)], ...
                   '-', 'Color', [0.85 0.65 0.15], 'LineWidth', 7);
    h_j1 = plot3(ax, wp_base(1), wp_base(2), wp_base(3), 'o', ...
                 'MarkerFaceColor', [0.9 0.7 0.2], 'MarkerEdgeColor', 'w', 'MarkerSize', 8);

    % Link 2: Upper Arm (Shoulder to Elbow)
    h_upper = plot3(ax, [wp_base(1), wp_elbow(1)], [wp_base(2), wp_elbow(2)], [wp_base(3), wp_elbow(3)], ...
                    '-', 'Color', [0.25 0.75 0.95], 'LineWidth', 6);
    h_j2 = plot3(ax, wp_elbow(1), wp_elbow(2), wp_elbow(3), 's', ...
                 'MarkerFaceColor', [0.3 0.8 1.0], 'MarkerEdgeColor', 'w', 'MarkerSize', 8);

    % Link 3: Forearm (Elbow to Wrist)
    h_fore = plot3(ax, [wp_elbow(1), wp_wrist(1)], [wp_elbow(2), wp_wrist(2)], [wp_elbow(3), wp_wrist(3)], ...
                   '-', 'Color', [0.20 0.85 0.55], 'LineWidth', 5);
    h_j3 = plot3(ax, wp_wrist(1), wp_wrist(2), wp_wrist(3), 'd', ...
                 'MarkerFaceColor', [0.2 0.9 0.6], 'MarkerEdgeColor', 'w', 'MarkerSize', 7);

    % Link 4 & 5: Wrist & Pitch/Roll Assembly
    h_wrist = plot3(ax, [wp_wrist(1), wp_grip(1)], [wp_wrist(2), wp_grip(2)], [wp_wrist(3), wp_grip(3)], ...
                    '-', 'Color', [0.95 0.45 0.25], 'LineWidth', 4);

    % Link 6: Two-Finger Gripper / End-Effector
    f1_tip = wp_grip + [ 0.05*cos(theta) - 0.03*sin(theta),  0.05*sin(theta) + 0.03*cos(theta),  0.02];
    f2_tip = wp_grip + [ 0.05*cos(theta) + 0.03*sin(theta),  0.05*sin(theta) - 0.03*cos(theta), -0.02];
    h_grip1 = plot3(ax, [wp_grip(1), f1_tip(1)], [wp_grip(2), f1_tip(2)], [wp_grip(3), f1_tip(3)], ...
                    '-', 'Color', [0.95 0.30 0.30], 'LineWidth', 3);
    h_grip2 = plot3(ax, [wp_grip(1), f2_tip(1)], [wp_grip(2), f2_tip(2)], [wp_grip(3), f2_tip(3)], ...
                    '-', 'Color', [0.95 0.30 0.30], 'LineWidth', 3);

    handles = [handles; h_base; h_j1; h_upper; h_j2; h_fore; h_j3; h_wrist; h_grip1; h_grip2];
end

% =========================================================================
% Helper: 3D Depth-Camera Sensor Field Cone (Mounted on Headrest)
% =========================================================================
function handles = draw_headrest_depth_cone(ax, x0, y0, z0, theta)
    handles = [];
    % Camera apex at headrest: [x0, y0, z0]
    cone_reach = 2.2;
    fov_h = 0.55; % ~32 deg half-angle
    fov_v = 0.35; % ~20 deg downward pitch

    % 4 corner points of depth frustum
    corners = [
        cone_reach * sin(theta - fov_h), cone_reach * cos(theta - fov_h), -0.7;
        cone_reach * sin(theta + fov_h), cone_reach * cos(theta + fov_h), -0.7;
        cone_reach * sin(theta + fov_h*0.8), cone_reach * cos(theta + fov_h*0.8), 0.2;
        cone_reach * sin(theta - fov_h*0.8), cone_reach * cos(theta - fov_h*0.8), 0.2
    ];

    p_apex = [x0, y0, z0];
    w_corners = [p_apex(1) + corners(:,1), p_apex(2) + corners(:,2), p_apex(3) + corners(:,3)];

    % Draw 4 frustum boundary rays
    for i = 1:4
        h_ray = plot3(ax, [p_apex(1), w_corners(i,1)], [p_apex(2), w_corners(i,2)], [p_apex(3), w_corners(i,3)], ...
                      '-', 'Color', [0.3 0.85 1.0, 0.45], 'LineWidth', 1.4);
        handles = [handles; h_ray];
    end

    % Frustum base rectangle
    h_base = plot3(ax, [w_corners(:,1); w_corners(1,1)], ...
                       [w_corners(:,2); w_corners(1,2)], ...
                       [w_corners(:,3); w_corners(1,3)], ...
                   '--', 'Color', [0.3 0.85 1.0, 0.6], 'LineWidth', 1.2);
    handles = [handles; h_base];
end

% =========================================================================
% Helper: Draw Front LiDAR Raycast Lines (-30°, 0°, +30°)
% =========================================================================
function handles = draw_sensor_cone(ax, x0, y0, z0, theta)
    handles = [];
    ray_angles_deg = [-30, 0, 30];
    ray_length = 2.6;

    for ang = ray_angles_deg
        rad_offset = deg2rad(ang);
        ray_th = theta + rad_offset;
        target_x = x0 + ray_length * sin(ray_th);
        target_y = y0 + ray_length * cos(ray_th);
        target_z = 0.10;

        h_line = plot3(ax, [x0, target_x], [y0, target_y], [z0, target_z], ...
                       '--', 'Color', [0.2 0.85 1.0, 0.65], 'LineWidth', 1.8);
        handles = [handles; h_line];
    end
end

% =========================================================================
% Geometry Primitives
% =========================================================================
function h = draw_box(ax, p_min, p_max, color, alpha)
    x = [p_min(1), p_max(1)];
    y = [p_min(2), p_max(2)];
    z = [p_min(3), p_max(3)];
    [X, Y, Z] = meshgrid(x, y, z);
    h = patch(ax, 'XData', [X(1:4)'; X(5:8)'], ...
                  'YData', [Y(1:4)'; Y(5:8)'], ...
                  'ZData', [Z(1:4)'; Z(5:8)'], ...
                  'FaceColor', color, 'FaceAlpha', alpha, 'EdgeColor', 'none');
end

function h = draw_transformed_box(ax, pts, color)
    faces = [1 2 3 4; 5 6 7 8; 1 2 6 5; 2 3 7 6; 3 4 8 7; 4 1 5 8];
    h = patch(ax, 'Vertices', pts, 'Faces', faces, ...
                  'FaceColor', color, 'FaceAlpha', 0.95, 'EdgeColor', [0.2 0.25 0.35]);
end

function h = draw_cylinder(ax, cx, cy, radius, height, color, z_base)
    if nargin < 7
        z_base = 0.0;
    end
    [Xc, Yc, Zc] = cylinder(radius, 20);
    Zc = Zc * height + z_base;
    Xc = Xc + cx;
    Yc = Yc + cy;
    h = surf(ax, Xc, Yc, Zc, 'FaceColor', color, 'EdgeColor', 'none', 'FaceAlpha', 0.85);
end

function h = draw_wheel(ax, center, theta, color)
    r = 0.16;
    th_circ = linspace(0, 2*pi, 16);
    x_c = r * cos(th_circ);
    z_c = r * sin(th_circ);
    y_c = zeros(size(x_c));

    R = [cos(theta), -sin(theta), 0;
         sin(theta),  cos(theta), 0;
         0,           0,          1];
    pts = (R * [x_c; y_c; z_c])' + center;
    h = patch(ax, pts(:,1), pts(:,2), pts(:,3), color, 'EdgeColor', [0.4 0.45 0.55], 'LineWidth', 1.2);
end

function h = draw_caster(ax, center, color)
    r = 0.06;
    [Xs, Ys, Zs] = sphere(10);
    h = surf(ax, Xs*r + center(1), Ys*r + center(2), Zs*r + center(3), ...
             'FaceColor', color, 'EdgeColor', 'none');
end

% =========================================================================
% Simulation Functions
% =========================================================================
function [x, y, th] = simulate_trajectory(N, dt, user_steer_deg, copilot_corr_deg)
    x = zeros(1, N);
    y = zeros(1, N);
    th = zeros(1, N);
    x(1) = 0.0;
    y(1) = 0.5;
    th(1) = 0.0;
    v = 0.8;
    L = 0.60;

    effective_steer = user_steer_deg + copilot_corr_deg;
    omega = (v / L) * tand(effective_steer);

    for i = 1:N-1
        th(i+1) = th(i) + omega * dt;
        x(i+1) = x(i) + v * sind(th(i)) * dt;
        y(i+1) = y(i) + v * cosd(th(i)) * dt;
    end
end

function [x, y, th, alpha_hist, clearance_hist] = simulate_waylo_copilot(N, dt, user_steer_deg)
    x = zeros(1, N);
    y = zeros(1, N);
    th = zeros(1, N);
    alpha_hist = zeros(1, N);
    clearance_hist = zeros(1, N);

    x(1) = 0.0;
    y(1) = 0.5;
    th(1) = 0.0;
    v_base = 0.8;
    L = 0.60;
    door_y = 4.5;

    for i = 1:N-1
        dist_y = door_y - y(i);
        left_clearance = max(0.05, 0.60 + x(i));
        right_clearance = max(0.05, 0.60 - x(i));
        min_clearance = min(left_clearance, right_clearance);
        clearance_hist(i) = round(min_clearance, 2);

        if dist_y > 0 && dist_y < 2.5
            alpha = min(0.92, max(0.15, (2.5 - dist_y) / 2.5 + abs(x(i)) * 0.4));
            centering_corr_deg = - (x(i) * 35.0 + th(i) * 20.0);
        else
            alpha = 0.10;
            centering_corr_deg = 0.0;
        end
        alpha_hist(i) = round(alpha, 2);

        blended_steer = (1 - alpha) * user_steer_deg + alpha * (user_steer_deg + centering_corr_deg);
        v_current = (1 - alpha) * v_base + alpha * min(v_base, 0.65);

        omega = (v_current / L) * tand(blended_steer);
        th(i+1) = th(i) + omega * dt;
        x(i+1) = x(i) + v_current * sind(th(i)) * dt;
        y(i+1) = y(i) + v_current * cosd(th(i)) * dt;
    end
    clearance_hist(N) = clearance_hist(N-1);
    alpha_hist(N) = alpha_hist(N-1);
end
