%% =========================================================================
% WAYLO: Physical Differential-Drive Kinematics & Shared-Autonomy Simulation
% NVIDIA x Nebius Global AI Hackathon (Physical AI Track)
%
% Differential Drive Kinematics Equations:
%   dx/dt     = v * cos(theta)
%   dy/dt     = v * sin(theta)
%   dtheta/dt = omega = (v_R - v_L) / L
%
% Numerical ODE Solver: 4th-Order Runge-Kutta (RK4)
% Benchmarks:
%   - Unassisted human steering drift (collision course with door jamb)
%   - WAYLO shared-autonomy arbitration (centered doorway clearance)
% =========================================================================

function waylo_kinematics_sim()
    clear; close all; clc;

    fprintf('========================================================\n');
    fprintf('  WAYLO: Physical Differential-Drive Kinematics Sim\n');
    fprintf('  Shared-Autonomy Arbitration Model Benchmark\n');
    fprintf('  Platform: Power Wheelchair (L=0.60m, r=0.16m, m=110kg)\n');
    fprintf('========================================================\n\n');

    % --- 1. Vehicle & Simulation Parameters ---
    params.L = 0.60;               % Wheelbase / track width L (meters)
    params.r = 0.16;               % Wheel radius r (meters)
    params.v_max = 1.5;            % Max linear speed (m/s)
    params.w_max = 1.5;            % Max angular velocity (rad/s)
    params.a_max = 2.0;            % Max braking deceleration (m/s^2)
    params.door_y = 4.5;           % Target doorway forward position Y (meters)
    params.door_width = 1.20;      % 1.2m clear doorway opening
    params.door_half_w = params.door_width / 2.0; % 0.60m half-width
    params.min_clearance_safe = 0.35; % Safe lateral clearance margin (meters)

    dt = 0.02;                     % Time step (seconds) - 50 Hz control loop
    t_end = 6.0;                   % Simulation duration (seconds)
    time = 0:dt:t_end;
    N = length(time);

    % --- 2. Initial State [x; y; theta] ---
    % Starting at x=0, y=0.5m, facing forward along Y-axis (theta = pi/2 rad = 90 deg)
    x0 = 0.0;
    y0 = 0.5;
    th0 = pi/2;

    % Driver drift profile: involuntary steering drift = -16 degrees (drifting right)
    steer_drift_deg = -16.0;
    v_user_cmd = 0.85; % Linear velocity input (m/s)

    % --- 3. Scenario A: Unassisted Human Driver (No WAYLO Copilot) ---
    fprintf('Simulating Scenario A: Unassisted Human Drift (drift = %.1f°)...\n', steer_drift_deg);
    state_unassisted = zeros(3, N);
    wheels_unassisted = zeros(2, N); % [omega_L; omega_R] in rad/s
    clearance_unassisted = zeros(1, N);
    collision_unassisted = false;

    state_unassisted(:, 1) = [x0; y0; th0];

    for k = 1:N-1
        x = state_unassisted(1, k);
        y = state_unassisted(2, k);
        th = state_unassisted(3, k);

        % Driver commanded turning rate
        omega_user = (v_user_cmd / params.L) * tand(steer_drift_deg);
        v_act = v_user_cmd;

        % Wheel linear velocities: v_R = v + (omega*L)/2, v_L = v - (omega*L)/2
        v_r = v_act + (omega_user * params.L / 2.0);
        v_l = v_act - (omega_user * params.L / 2.0);

        % Wheel angular speeds: omega_L = v_L / r, omega_R = v_R / r
        wheels_unassisted(:, k) = [v_l / params.r; v_r / params.r];

        % Integrate differential drive kinematics using 4th-Order Runge-Kutta
        state_unassisted(:, k+1) = rk4_step(@kinematics_deriv, state_unassisted(:, k), v_act, omega_user, dt);

        % Clearance to 1.2m doorway
        dist_y = params.door_y - y;
        if abs(dist_y) < 0.25
            c_l = params.door_half_w + x;
            c_r = params.door_half_w - x;
            c_min = min(c_l, c_r);
            clearance_unassisted(k) = c_min;
            if c_min <= 0.0
                collision_unassisted = true;
            end
        else
            clearance_unassisted(k) = params.door_half_w - abs(x);
        end
    end
    clearance_unassisted(N) = clearance_unassisted(N-1);
    wheels_unassisted(:, N) = wheels_unassisted(:, N-1);

    % --- 4. Scenario B: WAYLO Shared-Autonomy Copilot Active ---
    fprintf('Simulating Scenario B: WAYLO Shared-Autonomy Active...\n');
    state_waylo = zeros(3, N);
    wheels_waylo = zeros(2, N); % [omega_L; omega_R] in rad/s
    alpha_history = zeros(1, N);
    clearance_waylo = zeros(1, N);
    collision_waylo = false;

    state_waylo(:, 1) = [x0; y0; th0];

    for k = 1:N-1
        x = state_waylo(1, k);
        y = state_waylo(2, k);
        th = state_waylo(3, k);

        % Distance to doorway threshold plane
        dist_to_door = params.door_y - y;

        % Clearance margins
        c_left = params.door_half_w + x;
        c_right = params.door_half_w - x;
        min_clear = min(c_left, c_right);
        clearance_waylo(k) = min_clear;

        % Human unassisted angular velocity command
        omega_user = (v_user_cmd / params.L) * tand(steer_drift_deg);

        % WAYLO Perception & Control Computation: centering target (x=0, theta=pi/2)
        heading_err = (pi/2) - th;
        lateral_err = 0.0 - x;

        % Copilot centering controller
        kp_lat = 2.4;
        kp_head = 1.8;
        omega_copilot = kp_lat * lateral_err + kp_head * heading_err;
        omega_copilot = max(-params.w_max, min(params.w_max, omega_copilot));

        % Adaptive Shared Autonomy Arbitration Alpha (t)
        if dist_to_door > 0 && dist_to_door < 3.2
            proximity_weight = (3.2 - dist_to_door) / 3.2;
            clearance_deficit = max(0.0, (params.min_clearance_safe - min_clear) / params.min_clearance_safe);
            alpha = min(0.95, max(0.05, 0.40 * proximity_weight + 0.60 * clearance_deficit));
            v_copilot = max(0.40, v_user_cmd * (1.0 - 0.4 * clearance_deficit));
        elseif dist_to_door <= 0
            % Past doorway: smoothly transfer authority back to human
            alpha = max(0.05, 0.40 * exp(-abs(dist_to_door)));
            v_copilot = v_user_cmd;
        else
            alpha = 0.05;
            v_copilot = v_user_cmd;
        end
        alpha_history(k) = alpha;

        % Shared-Autonomy Blending:
        % v_final     = (1 - alpha) * v_user + alpha * v_copilot
        % omega_final = (1 - alpha) * omega_user + alpha * omega_copilot
        v_final = (1.0 - alpha) * v_user_cmd + alpha * v_copilot;
        omega_final = (1.0 - alpha) * omega_user + alpha * omega_copilot;

        % Wheel speeds from differential drive equations:
        % v_R = v + (omega*L)/2, v_L = v - (omega*L)/2
        v_r = v_final + (omega_final * params.L / 2.0);
        v_l = v_final - (omega_final * params.L / 2.0);

        % Wheel angular velocities (omega_L, omega_R)
        omega_L = v_l / params.r;
        omega_R = v_r / params.r;
        wheels_waylo(:, k) = [omega_L; omega_R];

        % 4th-Order Runge-Kutta numerical ODE integration
        state_waylo(:, k+1) = rk4_step(@kinematics_deriv, state_waylo(:, k), v_final, omega_final, dt);

        if abs(dist_to_door) < 0.25 && min_clear <= 0.0
            collision_waylo = true;
        end
    end
    alpha_history(N) = alpha_history(N-1);
    clearance_waylo(N) = clearance_waylo(N-1);
    wheels_waylo(:, N) = wheels_waylo(:, N-1);

    % --- 5. Publish Quantitative Results ---
    fprintf('\n================== SIMULATION BENCHMARK ==================\n');
    fprintf('Metric                          Unassisted    WAYLO Copilot\n');
    fprintf('--------------------------------------------------------\n');
    fprintf('Min Doorway Clearance (m):      %+7.2f       %+7.2f\n', min(clearance_unassisted), min(clearance_waylo));
    fprintf('Lateral Deviation at Door (m):  %+7.2f       %+7.2f\n', ...
            state_unassisted(1, round(N*0.75)), state_waylo(1, round(N*0.75)));
    if collision_unassisted
        col_un = 'COLLISION DETECTED';
    else
        col_un = 'SAFE';
    end
    if collision_waylo
        col_w = 'COLLISION';
    else
        col_w = 'SAFE (ZERO IMPACT)';
    end
    fprintf('Collision Outcome:             %s   %s\n', col_un, col_w);
    fprintf('Peak Copilot Authority alpha:       ---             %0.2f\n', max(alpha_history));
    fprintf('========================================================\n\n');

    % --- 6. Side-by-Side Publication Figures ---
    fig = figure('Name', 'WAYLO Kinematics & Wheel Speed Benchmark', ...
                 'Color', [0.08 0.10 0.15], 'Position', [60, 40, 1280, 720]);

    % Subplot 1: Side-by-Side Trajectory Comparison
    ax1 = subplot(1, 2, 1);
    hold(ax1, 'on'); grid(ax1, 'on');
    set(ax1, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);

    % Draw walls and 1.2m doorway
    plot(ax1, [-3, -params.door_half_w], [params.door_y, params.door_y], 'Color', [0.5 0.55 0.65], 'LineWidth', 4);
    plot(ax1, [params.door_half_w, 3], [params.door_y, params.door_y], 'Color', [0.5 0.55 0.65], 'LineWidth', 4);
    plot(ax1, [-params.door_half_w, params.door_half_w], [params.door_y, params.door_y], '--', 'Color', [0.2 0.85 0.4], 'LineWidth', 2.5);

    % Doorway jamb markers
    plot(ax1, -params.door_half_w, params.door_y, 'ks', 'MarkerFaceColor', [0.9 0.4 0.2], 'MarkerSize', 8);
    plot(ax1, params.door_half_w, params.door_y, 'ks', 'MarkerFaceColor', [0.9 0.4 0.2], 'MarkerSize', 8);
    text(ax1, 0.0, params.door_y + 0.35, '1.2m DOORWAY', 'Color', [0.6 0.95 0.7], ...
         'FontSize', 9, 'FontWeight', 'bold', 'HorizontalAlignment', 'center');

    % Trajectory curves
    p1 = plot(ax1, state_unassisted(1, :), state_unassisted(2, :), '--', 'Color', [0.95 0.3 0.4], 'LineWidth', 2.4);
    p2 = plot(ax1, state_waylo(1, :), state_waylo(2, :), '-', 'Color', [0.15 0.85 0.45], 'LineWidth', 3.0);

    xlabel(ax1, 'Lateral Position X (meters)', 'FontWeight', 'bold');
    ylabel(ax1, 'Forward Position Y (meters)', 'FontWeight', 'bold');
    title(ax1, {'\bf2D Spatial Trajectory Curves', '\rmUnassisted Human Drift vs. WAYLO Centered Path'}, ...
          'Color', 'white', 'FontSize', 12);
    legend(ax1, [p1, p2], {'Unassisted Human Drift (Collision Course)', 'WAYLO Copilot (Centered Clearance)'}, ...
           'Location', 'northwest', 'TextColor', 'white', 'Color', [0.15 0.18 0.26]);
    axis(ax1, [-2.2, 2.2, 0.0, 6.0]);

    % Subplot 2: Side-by-Side Wheel Angular Speeds (omega_L, omega_R)
    ax2 = subplot(1, 2, 2);
    hold(ax2, 'on'); grid(ax2, 'on');
    set(ax2, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);

    % Wheel angular speeds for Unassisted vs WAYLO
    w1 = plot(ax2, time, wheels_unassisted(1, :), ':', 'Color', [0.95 0.4 0.4], 'LineWidth', 1.8);
    w2 = plot(ax2, time, wheels_unassisted(2, :), ':', 'Color', [0.95 0.7 0.3], 'LineWidth', 1.8);
    w3 = plot(ax2, time, wheels_waylo(1, :), '-', 'Color', [0.35 0.75 1.0], 'LineWidth', 2.4);
    w4 = plot(ax2, time, wheels_waylo(2, :), '-', 'Color', [0.2 0.9 0.5], 'LineWidth', 2.4);

    xlabel(ax2, 'Time (seconds)', 'FontWeight', 'bold');
    ylabel(ax2, 'Wheel Angular Speed \omega (rad/s)', 'FontWeight', 'bold');
    title(ax2, {'\bfWheel Angular Speeds (\omega_L, \omega_R)', '\rmDifferential Actuation: (v_R - v_L)/L Arbitration'}, ...
          'Color', 'white', 'FontSize', 12);
    legend(ax2, [w1, w2, w3, w4], ...
           {'Unassisted \omega_L', 'Unassisted \omega_R', 'WAYLO Assisted \omega_L', 'WAYLO Assisted \omega_R'}, ...
           'Location', 'best', 'TextColor', 'white', 'Color', [0.15 0.18 0.26]);

    % Figure Super Title
    sgtitle(fig, 'WAYLO: Differential Drive Kinematics & Runge-Kutta ODE Solver', ...
            'Color', 'white', 'FontSize', 14, 'FontWeight', 'bold');
end

% =========================================================================
% Differential Drive Kinematics Equations:
%   dx/dt     = v * cos(theta)
%   dy/dt     = v * sin(theta)
%   dtheta/dt = omega = (v_R - v_L) / L
% =========================================================================
function dx = kinematics_deriv(state, v, omega)
    theta = state(3);
    dx = [v * cos(theta);
          v * sin(theta);
          omega];
end

% =========================================================================
% Numerical 4th-Order Runge-Kutta (RK4) ODE Integrator
% =========================================================================
function x_next = rk4_step(f, x, v, omega, dt)
    k1 = f(x, v, omega);
    k2 = f(x + 0.5 * dt * k1, v, omega);
    k3 = f(x + 0.5 * dt * k2, v, omega);
    k4 = f(x + dt * k3, v, omega);
    x_next = x + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4);
end
