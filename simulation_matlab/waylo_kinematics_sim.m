%% =========================================================================
% WAYLO: Physical Differential-Drive Kinematics & Shared-Autonomy Simulation
% NVIDIA x Nebius Global AI Hackathon (Physical AI Track)
%
% Mathematical Model:
%   dx/dt     = v * cos(theta)
%   dy/dt     = v * sin(theta)
%   dtheta/dt = omega = (v_R - v_L) / L
%
% Shared-Autonomy Arbitration:
%   v_final     = (1 - alpha) * v_user + alpha * v_copilot
%   omega_final = (1 - alpha) * omega_user + alpha * omega_copilot
%   alpha in [0, 1] scaled by dynamic spatial hazard risk
% =========================================================================

function waylo_kinematics_sim()
    clear; close all; clc;

    fprintf('========================================================\n');
    fprintf('  WAYLO: Physical Differential-Drive Kinematics Sim\n');
    fprintf('  Shared-Autonomy Arbitration Model Benchmark\n');
    fprintf('  Platform: Power Wheelchair (L=0.60m, r=0.16m, m=110kg)\n');
    fprintf('========================================================\n\n');

    % --- 1. Vehicle & Simulation Parameters ---
    params.L = 0.60;               % Wheelbase / track width (m)
    params.r = 0.16;               % Wheel radius (m)
    params.v_max = 1.5;            % Max linear speed (m/s)
    params.w_max = 1.5;            % Max angular velocity (rad/s)
    params.a_max = 2.0;            % Max deceleration (m/s^2)
    params.door_y = 4.5;           % Doorway forward position (m)
    params.door_half_w = 0.70;     % Door opening half-width (1.4m total)
    params.min_clearance_safe = 0.35; % Desired minimum safety margin (m)

    dt = 0.02;                     % Time step (seconds) - 50 Hz control loop
    t_end = 6.0;                   % Simulation duration (seconds)
    time = 0:dt:t_end;
    N = length(time);

    % --- 2. Initial State [x; y; theta] ---
    % Starting at x=0, y=0.5m, facing forward (theta = pi/2)
    x0 = 0.0;
    y0 = 0.5;
    th0 = pi/2; % 90 deg (forward along Y-axis)

    % Human driver profile: applies steering deviation (e.g. involuntary tremor or drift)
    % Drifts right with steering command = -16 degrees
    steer_drift_deg = -16.0;
    v_user_cmd = 0.85; % m/s

    % --- 3. Run Simulation 1: Unassisted Human Driver (No WAYLO) ---
    fprintf('Simulating Scenario A: Unassisted Human Driver (drift = %.1f°)...\n', steer_drift_deg);
    state_unassisted = zeros(3, N);
    wheels_unassisted = zeros(2, N); % [v_L, v_R]
    clearance_unassisted = zeros(1, N);
    collision_unassisted = false;

    state_unassisted(:, 1) = [x0; y0; th0];

    for k = 1:N-1
        x = state_unassisted(1, k);
        y = state_unassisted(2, k);
        th = state_unassisted(3, k);

        % Unassisted omega from user steering
        omega_user = (v_user_cmd / params.L) * tand(steer_drift_deg);
        v_act = v_user_cmd;

        % Wheel speeds
        v_r = v_act + (omega_user * params.L / 2.0);
        v_l = v_act - (omega_user * params.L / 2.0);
        wheels_unassisted(:, k) = [v_l; v_r] / params.r; % rad/s

        % Integrate kinematics (Runge-Kutta 4th Order)
        state_unassisted(:, k+1) = rk4_step(@kinematics_deriv, state_unassisted(:, k), v_act, omega_user, dt);

        % Check clearance at doorway
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
            clearance_unassisted(k) = 0.70 - abs(x);
        end
    end
    clearance_unassisted(N) = clearance_unassisted(N-1);
    wheels_unassisted(:, N) = wheels_unassisted(:, N-1);

    % --- 4. Run Simulation 2: WAYLO Shared-Autonomy Copilot ---
    fprintf('Simulating Scenario B: WAYLO Shared-Autonomy Active...\n');
    state_waylo = zeros(3, N);
    wheels_waylo = zeros(2, N);
    alpha_history = zeros(1, N);
    clearance_waylo = zeros(1, N);
    omega_cmd_history = zeros(2, N); % [user_omega, copilot_omega]
    collision_waylo = false;

    state_waylo(:, 1) = [x0; y0; th0];

    for k = 1:N-1
        x = state_waylo(1, k);
        y = state_waylo(2, k);
        th = state_waylo(3, k);

        % Current clearance to doorway threshold
        c_left = params.door_half_w + x;
        c_right = params.door_half_w - x;
        min_clear = min(c_left, c_right);
        clearance_waylo(k) = min_clear;

        % Distance to doorway plane
        dist_to_door = params.door_y - y;

        % User inputs
        omega_user = (v_user_cmd / params.L) * tand(steer_drift_deg);

        % WAYLO Perception & Control Computation
        % Centering goal: target x = 0.0, target theta = pi/2
        heading_err = (pi/2) - th;
        lateral_err = 0.0 - x;

        % PD centering controller for copilot
        kp_lat = 2.4;
        kp_head = 1.8;
        omega_copilot = kp_lat * lateral_err + kp_head * heading_err;
        omega_copilot = max(-params.w_max, min(params.w_max, omega_copilot));

        % Adaptive Shared Autonomy Arbitration Alpha (t)
        if dist_to_door > 0 && dist_to_door < 3.2
            proximity_weight = (3.2 - dist_to_door) / 3.2;
            lateral_penalty = max(0.0, (params.min_clearance_safe - min_clear) / params.min_clearance_safe);
            alpha = min(0.95, max(0.05, 0.40 * proximity_weight + 0.60 * lateral_penalty));
            v_copilot = max(0.40, v_user_cmd * (1.0 - 0.4 * lateral_penalty));
        elseif dist_to_door <= 0
            % Cleared doorway, return full authority back to human
            alpha = max(0.05, 0.40 * exp(-abs(dist_to_door)));
            v_copilot = v_user_cmd;
        else
            alpha = 0.05;
            v_copilot = v_user_cmd;
        end
        alpha_history(k) = alpha;

        % Mathematical Shared-Autonomy Blending:
        % v_blend     = (1 - alpha) * v_user + alpha * v_copilot
        % omega_blend = (1 - alpha) * omega_user + alpha * omega_copilot
        v_blend = (1.0 - alpha) * v_user_cmd + alpha * v_copilot;
        omega_blend = (1.0 - alpha) * omega_user + alpha * omega_copilot;

        % Wheel speeds
        v_r = v_blend + (omega_blend * params.L / 2.0);
        v_l = v_blend - (omega_blend * params.L / 2.0);
        wheels_waylo(:, k) = [v_l; v_r] / params.r; % rad/s
        omega_cmd_history(:, k) = [omega_user; omega_copilot];

        % Integrate kinematics (RK4)
        state_waylo(:, k+1) = rk4_step(@kinematics_deriv, state_waylo(:, k), v_blend, omega_blend, dt);

        if abs(dist_to_door) < 0.25 && min_clear <= 0.0
            collision_waylo = true;
        end
    end
    alpha_history(N) = alpha_history(N-1);
    clearance_waylo(N) = clearance_waylo(N-1);
    wheels_waylo(:, N) = wheels_waylo(:, N-1);

    % --- 5. Publish Quantitative Results ---
    fprintf('\n================== SIMULATION RESULTS ==================\n');
    fprintf('Metric                          Unassisted    WAYLO Copilot\n');
    fprintf('--------------------------------------------------------\n');
    fprintf('Min Doorway Clearance (m):      %+7.2f       %+7.2f\n', min(clearance_unassisted), min(clearance_waylo));
    fprintf('Lateral Deviation at Door (m):  %+7.2f       %+7.2f\n', ...
            state_unassisted(1, round(N*0.75)), state_waylo(1, round(N*0.75)));
    if collision_unassisted
        col_str_un = 'COLLISION DETECTED';
    else
        col_str_un = 'SAFE';
    end

    if collision_waylo
        col_str_w = 'COLLISION DETECTED';
    else
        col_str_w = 'SAFE (ZERO IMPACT)';
    end
    fprintf('Collision Outcome:             %s   %s\n', col_str_un, col_str_w);
    fprintf('Max Blended Authority alpha:        ---             %0.2f\n', max(alpha_history));
    fprintf('========================================================\n\n');

    % --- 6. Plot Publication-Quality Figures ---
    fig = figure('Name', 'WAYLO Kinematics & Shared-Autonomy Benchmark', ...
                 'Color', [0.08 0.10 0.15], 'Position', [80, 50, 1200, 800]);

    % Subplot 1: 2D Spatial Trajectory
    ax1 = subplot(2, 2, 1);
    hold(ax1, 'on'); grid(ax1, 'on');
    set(ax1, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);
    
    % Draw door walls
    plot(ax1, [-3, -0.7], [params.door_y, params.door_y], 'Color', [0.5 0.55 0.65], 'LineWidth', 4);
    plot(ax1, [0.7, 3], [params.door_y, params.door_y], 'Color', [0.5 0.55 0.65], 'LineWidth', 4);
    % Door opening line
    plot(ax1, [-0.7, 0.7], [params.door_y, params.door_y], '--', 'Color', [0.2 0.85 0.4], 'LineWidth', 2);
    
    % Plot trajectories
    p1 = plot(ax1, state_unassisted(1, :), state_unassisted(2, :), '--', 'Color', [0.95 0.3 0.4], 'LineWidth', 2.2);
    p2 = plot(ax1, state_waylo(1, :), state_waylo(2, :), '-', 'Color', [0.15 0.85 0.45], 'LineWidth', 2.8);
    
    % Doorway posts markers
    plot(ax1, -0.7, params.door_y, 'ks', 'MarkerFaceColor', [0.9 0.4 0.2], 'MarkerSize', 8);
    plot(ax1, 0.7, params.door_y, 'ks', 'MarkerFaceColor', [0.9 0.4 0.2], 'MarkerSize', 8);
    
    xlabel(ax1, 'Lateral Position X (m)', 'FontWeight', 'bold');
    ylabel(ax1, 'Forward Position Y (m)', 'FontWeight', 'bold');
    title(ax1, '1. 2D Spatial Trajectory Comparison', 'Color', 'white', 'FontSize', 11);
    legend(ax1, [p1, p2], {'Unassisted (Collision Course)', 'WAYLO Copilot (Centered)'}, ...
           'Location', 'northwest', 'TextColor', 'white', 'Color', [0.15 0.18 0.26]);
    axis(ax1, [-2.0, 2.0, 0.0, 6.0]);

    % Subplot 2: Heading Angle theta(t)
    ax2 = subplot(2, 2, 2);
    hold(ax2, 'on'); grid(ax2, 'on');
    set(ax2, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);
    plot(ax2, time, rad2deg(state_unassisted(3, :)), '--', 'Color', [0.95 0.3 0.4], 'LineWidth', 2.0);
    plot(ax2, time, rad2deg(state_waylo(3, :)), '-', 'Color', [0.15 0.85 0.45], 'LineWidth', 2.5);
    yline(ax2, 90, ':', 'Color', [0.4 0.8 1.0], 'LineWidth', 1.5);
    xlabel(ax2, 'Time (seconds)', 'FontWeight', 'bold');
    ylabel(ax2, 'Heading Angle \theta (deg)', 'FontWeight', 'bold');
    title(ax2, '2. Wheelchair Orientation vs Time', 'Color', 'white', 'FontSize', 11);
    legend(ax2, {'Unassisted', 'WAYLO Assisted', 'Nominal Forward (90°)'}, ...
           'Location', 'southwest', 'TextColor', 'white', 'Color', [0.15 0.18 0.26]);

    % Subplot 3: Arbitration Weight Alpha & Clearance Margin
    ax3 = subplot(2, 2, 3);
    hold(ax3, 'on'); grid(ax3, 'on');
    set(ax3, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);
    yyaxis(ax3, 'left');
    set(ax3, 'YColor', [0.3 0.8 1.0]);
    plot(ax3, time, alpha_history, '-', 'Color', [0.3 0.8 1.0], 'LineWidth', 2.2);
    ylabel(ax3, 'Shared Autonomy Weight \alpha \in [0, 1]', 'FontWeight', 'bold');
    ylim(ax3, [0.0, 1.05]);

    yyaxis(ax3, 'right');
    set(ax3, 'YColor', [0.2 0.85 0.45]);
    plot(ax3, time, clearance_waylo, '-', 'Color', [0.2 0.85 0.45], 'LineWidth', 2.0);
    yline(ax3, params.min_clearance_safe, '--', 'Color', [0.9 0.8 0.2], 'LineWidth', 1.5);
    ylabel(ax3, 'Clearance Margin (m)', 'FontWeight', 'bold');
    xlabel(ax3, 'Time (seconds)', 'FontWeight', 'bold');
    title(ax3, '3. Dynamic Arbitration \alpha & Doorway Clearance', 'Color', 'white', 'FontSize', 11);

    % Subplot 4: Differential Drive Wheel Speeds
    ax4 = subplot(2, 2, 4);
    hold(ax4, 'on'); grid(ax4, 'on');
    set(ax4, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);
    plot(ax4, time, wheels_waylo(1, :), '-', 'Color', [0.4 0.6 0.95], 'LineWidth', 2.0);
    plot(ax4, time, wheels_waylo(2, :), '-', 'Color', [0.95 0.6 0.2], 'LineWidth', 2.0);
    xlabel(ax4, 'Time (seconds)', 'FontWeight', 'bold');
    ylabel(ax4, 'Wheel Speed \omega_{wheel} (rad/s)', 'FontWeight', 'bold');
    title(ax4, '4. Left & Right Wheel Actuator Speeds', 'Color', 'white', 'FontSize', 11);
    legend(ax4, {'Left Wheel (\omega_L)', 'Right Wheel (\omega_R)'}, ...
           'Location', 'northwest', 'TextColor', 'white', 'Color', [0.15 0.18 0.26]);

    % Overall Figure Super Title
    sgtitle(fig, 'WAYLO: Shared-Autonomy Kinematics & Physical Blending Benchmark', ...
            'Color', 'white', 'FontSize', 14, 'FontWeight', 'bold');
end

% =========================================================================
% Numerical Integration & Derivative Helpers
% =========================================================================
function dx = kinematics_deriv(state, v, omega)
    % state = [x; y; theta]
    theta = state(3);
    dx = [v * cos(theta);
          v * sin(theta);
          omega];
end

function x_next = rk4_step(f, x, v, omega, dt)
    % 4th-Order Runge-Kutta numerical integration
    k1 = f(x, v, omega);
    k2 = f(x + 0.5 * dt * k1, v, omega);
    k3 = f(x + 0.5 * dt * k2, v, omega);
    k4 = f(x + dt * k3, v, omega);
    x_next = x + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4);
end
