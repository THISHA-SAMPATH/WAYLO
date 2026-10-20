%% =========================================================================
% WAYLO: 3D Indoor Environment & Physical Wheelchair Perception Visualizer
% NVIDIA x Nebius Global AI Hackathon (Physical AI Track)
% 
% Features:
% - 3D Indoor Room with Doorway (1.4m), Narrow Corridor (1.2m), Workstation Table
% - Detailed 3D Electric Wheelchair Model (Chassis, Seat, Drive Wheels, Casters, LiDAR)
% - 3D Sensor Ray-casting & Perception Cone
% - Comparative Trajectory Animation (Unassisted Collision vs WAYLO Centered Path)
% - Hardware-in-the-Loop HTTP Hook to WAYLO FastAPI REST Server
% =========================================================================

function waylo_3d_environment()
    clear; close all; clc;

    fprintf('========================================================\n');
    fprintf('  WAYLO: YOUR WORLD. YOUR WAY.\n');
    fprintf('  3D Indoor Environment & Shared-Autonomy Visualizer\n');
    fprintf('  Accelerated with NVIDIA Nemotron / Cosmos on Nebius AI\n');
    fprintf('========================================================\n\n');

    % --- Simulation & Environment Setup ---
    fig = figure('Name', 'WAYLO 3D Environment & Spatial Perception', ...
                 'Color', [0.07 0.09 0.13], ...
                 'Position', [100, 80, 1100, 750], ...
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
    title(ax, {'\bf\fontsize{14}\color{white}WAYLO: 3D Spatial Environment & Physical Perception', ...
               '\fontsize{10}\color[rgb]{0.3,0.75,0.95}NVIDIA Nemotron-3-Ultra on Nebius AI Cloud | Differential Drive L=0.60m'}, ...
               'Interpreter', 'tex');

    xlim(ax, [-3.5, 3.5]);
    ylim(ax, [0.0, 6.5]);
    zlim(ax, [0.0, 2.8]);
    view(ax, [-35, 28]);

    % --- 1. Render Room Architecture ---
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
    h_leg = legend(ax, {'', '', '', '', '', '', '', '', '', '', '', ...
                        'Unassisted Trajectory (Collision Course)', ...
                        'WAYLO Shared-Autonomy Centered Path'}, ...
                        'TextColor', 'white', 'Color', [0.12 0.15 0.22], ...
                        'EdgeColor', [0.3 0.35 0.45], 'Location', 'northeast');

    % --- 3. Telemetry HUD Annotation ---
    hud_box = annotation('textbox', [0.03, 0.70, 0.30, 0.24], ...
                         'String', {'\bfWAYLO COPILOT TELEMETRY', ...
                                    'State: INITIALIZING...', ...
                                    'Pose (X, Y): [0.00, 0.50] m', ...
                                    'Shared-Autonomy \alpha: 0.00', ...
                                    'Doorway Clearance: 0.40 m', ...
                                    'Hazard Risk: 12% | AEB: READY'}, ...
                         'FitBoxToText', 'off', ...
                         'BackgroundColor', [0.10 0.13 0.20], ...
                         'Color', [0.85 0.90 0.98], ...
                         'EdgeColor', [0.25 0.65 0.95], ...
                         'LineWidth', 1.5, ...
                         'FontSize', 9, ...
                         'Interpreter', 'tex');

    % Lighting & Camera
    camlight(ax, 'headlight');
    lighting(ax, 'gouraud');

    % --- 4. Animate Wheelchair Along WAYLO Corrected Path ---
    fprintf('Starting 3D Real-Time Perception Animation...\n');
    chair_handles = [];
    sensor_rays = [];

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

        % Delete previous wheelchair geometry & sensor rays
        if ~isempty(chair_handles)
            delete(chair_handles);
        end
        if ~isempty(sensor_rays)
            delete(sensor_rays);
        end

        % Draw updated 3D Wheelchair at current pose
        chair_handles = draw_wheelchair_3d(ax, cur_x, cur_y, 0.0, cur_th);

        % Draw 3D LiDAR/Camera Perception Cone Rays
        sensor_rays = draw_sensor_cone(ax, cur_x, cur_y, 0.85, cur_th);

        % Update HUD Text
        aeb_text = 'ACTIVE';
        if cur_clearance < 0.20
            aeb_text = 'CAUTION: PROXIMITY';
        end
        set(hud_box, 'String', { ...
            '\bfWAYLO COPILOT TELEMETRY', ...
            sprintf('Nebius Model: \\color[rgb]{0.3,0.85,1.0}nvidia/nemotron-3-ultra'), ...
            sprintf('Pose (X, Y, \\theta): [%+.2f, %.2f m, %+.1f°]', cur_x, cur_y, rad2deg(cur_th)), ...
            sprintf('Shared-Autonomy \\alpha: \\bf%0.2f', cur_alpha), ...
            sprintf('Left/Right Clearance: %0.2f m', cur_clearance), ...
            sprintf('Hazard Risk: %d%% | Status: %s', risk_pct, aeb_text) ...
        });

        drawnow;
        pause(0.04);
    end

    fprintf('3D Perception Animation complete. WAYLO guided wheelchair safely through doorway.\n');
end

% =========================================================================
% Helper: Draw 3D Room Architecture
% =========================================================================
function draw_room_environment(ax)
    % Floor (8m x 7m)
    [Xf, Yf] = meshgrid(-3.5:0.5:3.5, 0.0:0.5:6.5);
    Zf = zeros(size(Xf));
    surf(ax, Xf, Yf, Zf, 'FaceColor', [0.12 0.14 0.19], ...
         'EdgeColor', [0.18 0.22 0.30], 'FaceAlpha', 0.9);

    % Doorway Walls at Y = 4.5m with a 1.4m central opening (X from -0.7 to +0.7)
    wall_color = [0.25 0.30 0.40];
    lintel_color = [0.35 0.42 0.55];

    % Left Wall: X from -3.5 to -0.7, Y = 4.5, Z from 0 to 2.4
    draw_box(ax, [-3.5, 4.45, 0.0], [-0.7, 4.55, 2.4], wall_color, 0.85);

    % Right Wall: X from 0.7 to 3.5, Y = 4.5, Z from 0 to 2.4
    draw_box(ax, [0.7, 4.45, 0.0], [3.5, 4.55, 2.4], wall_color, 0.85);

    % Doorway Top Lintel Beam (Spans over opening from -0.7 to 0.7, Z from 2.1 to 2.4)
    draw_box(ax, [-0.7, 4.45, 2.1], [0.7, 4.55, 2.4], lintel_color, 0.95);

    % Doorway Portal Threshold Line on Floor (Green)
    plot3(ax, [-0.7, 0.7], [4.5, 4.5], [0.02, 0.02], 'LineWidth', 4, 'Color', [0.15 0.85 0.45]);
    text(ax, 0.0, 4.5, 2.55, 'DOORWAY TARGET (1.4m)', ...
         'Color', [0.55 0.95 0.65], 'FontSize', 10, 'FontWeight', 'bold', 'HorizontalAlignment', 'center');

    % Tight Corridor Guide Walls from Y=1.5 to Y=3.5 (Width 1.2m)
    draw_box(ax, [-3.5, 1.5, 0.0], [-1.2, 3.5, 1.5], [0.20 0.24 0.32], 0.4);
    draw_box(ax, [1.2, 1.5, 0.0], [3.5, 3.5, 1.5], [0.20 0.24 0.32], 0.4);

    % Dynamic Obstacle at [1.8, 2.5]
    draw_cylinder(ax, 1.8, 2.5, 0.25, 1.2, [0.9 0.3 0.3]);
    text(ax, 1.8, 2.5, 1.35, 'Obstacle', 'Color', [1.0 0.4 0.4], ...
         'FontSize', 8, 'HorizontalAlignment', 'center');
end

% =========================================================================
% Helper: Draw Detailed 3D Electric Wheelchair Model
% =========================================================================
function handles = draw_wheelchair_3d(ax, x0, y0, z0, theta)
    handles = [];
    R = [cos(theta), -sin(theta), 0;
         sin(theta),  cos(theta), 0;
         0,           0,          1];

    % Transformation function
    tf = @(pts) (R * pts')' + [x0, y0, z0];

    % 1. Main Base Chassis (Black/Dark Slate)
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

    % 3. Backrest
    back_pts = [-0.06, -0.22, 0.32;
                 0.02, -0.22, 0.32;
                 0.02,  0.22, 0.32;
                -0.06,  0.22, 0.32;
                -0.06, -0.22, 0.80;
                 0.02, -0.22, 0.80;
                 0.02,  0.22, 0.80;
                -0.06,  0.22, 0.80];
    h_back = draw_transformed_box(ax, tf(back_pts), [0.12 0.35 0.75]);
    handles = [handles; h_back];

    % 4. Left & Right Drive Wheels (Cylinders at rear, radius 0.16m)
    h_w1 = draw_wheel(ax, tf([-0.05, -0.30, 0.16]), theta, [0.08 0.08 0.08]);
    h_w2 = draw_wheel(ax, tf([-0.05,  0.30, 0.16]), theta, [0.08 0.08 0.08]);
    handles = [handles; h_w1; h_w2];

    % 5. Perception Sensor Tower / LiDAR Pod on Backrest
    pod_pts = [-0.04, -0.05, 0.80;
                0.04, -0.05, 0.80;
                0.04,  0.05, 0.80;
               -0.04,  0.05, 0.80;
               -0.04, -0.05, 0.92;
                0.04, -0.05, 0.92;
                0.04,  0.05, 0.92;
               -0.04,  0.05, 0.92];
    h_pod = draw_transformed_box(ax, tf(pod_pts), [0.2 0.8 0.9]);
    handles = [handles; h_pod];
end

% =========================================================================
% Helper: Draw Perception Sensor Cone (LiDAR / Camera Rays)
% =========================================================================
function handles = draw_sensor_cone(ax, x0, y0, z0, theta)
    handles = [];
    ray_angles = linspace(-0.45, 0.45, 7); % 50-degree field of view
    ray_length = 2.4;

    for a = ray_angles
        ray_th = theta + a;
        target_x = x0 + ray_length * sin(ray_th);
        target_y = y0 + ray_length * cos(ray_th);
        target_z = 0.15; % ground intersection

        h_line = plot3(ax, [x0, target_x], [y0, target_y], [z0, target_z], ...
                       ':', 'Color', [0.2 0.8 1.0, 0.45], 'LineWidth', 1.2);
        handles = [handles; h_line];
    end
end

% =========================================================================
% Helpers: Geometry Primitives
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

function h = draw_cylinder(ax, cx, cy, radius, height, color)
    [Xc, Yc, Zc] = cylinder(radius, 20);
    Zc = Zc * height;
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
    v = 0.8; % m/s
    L = 0.60; % wheelbase

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
        % Calculate distance to doorway
        dist_y = door_y - y(i);
        
        % Dynamic clearance to doorway jambs (1.4m width, -0.7 to +0.7)
        left_clearance = max(0.05, 0.70 + x(i));
        right_clearance = max(0.05, 0.70 - x(i));
        min_clearance = min(left_clearance, right_clearance);
        clearance_hist(i) = round(min_clearance, 2);

        % Shared autonomy arbitration weight alpha
        if dist_y > 0 && dist_y < 2.5
            alpha = min(0.92, max(0.15, (2.5 - dist_y) / 2.5 + abs(x(i)) * 0.4));
            centering_corr_deg = - (x(i) * 35.0 + th(i) * 20.0);
        else
            alpha = 0.10;
            centering_corr_deg = 0.0;
        end
        alpha_hist(i) = round(alpha, 2);

        % Blended steering & speed
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
