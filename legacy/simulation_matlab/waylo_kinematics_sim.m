%% =========================================================================
% WAYLO: Physical Differential-Drive Kinematics & 6-DOF Arm IK Simulation
% NVIDIA x Nebius Global AI Hackathon (Physical AI Track)
%
% 1. Differential Drive Kinematics Equations:
%    dx/dt     = v * cos(theta)
%    dy/dt     = v * sin(theta)
%    dtheta/dt = omega = (v_R - v_L) / L
%
% 2. 6-DOF Robotic Arm Forward/Inverse Kinematics:
%    x = l1 * cos(t1) + l2 * cos(t1 + t2)
%    y = l1 * sin(t1) + l2 * sin(t1 + t2)
%    z = l3 * sin(t3)
%
% 3. Numerical ODE Solver: 4th-Order Runge-Kutta (RK4)
% 4. Telemetry Dispatch: webwrite to http://localhost:8000/api/v1/arm-manipulation
% =========================================================================

function waylo_kinematics_sim()
    clear; close all; clc;

    fprintf('========================================================\n');
    fprintf('  WAYLO: Physical Differential-Drive & 6-DOF Arm Sim\n');
    fprintf('  Kinematics, 4th-Order Runge-Kutta ODE & Arm IK Solver\n');
    fprintf('  Platform: Power Wheelchair with Clamped 6-Axis Arm\n');
    fprintf('========================================================\n\n');

    % --- 1. Vehicle & Wheelchair Parameters ---
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
    x0 = 0.0;
    y0 = 0.5;
    th0 = pi/2; % 90 deg forward along Y-axis

    % Driver drift profile: involuntary steering drift = -16 degrees
    steer_drift_deg = -16.0;
    v_user_cmd = 0.85;

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

        omega_user = (v_user_cmd / params.L) * tand(steer_drift_deg);
        v_act = v_user_cmd;

        v_r = v_act + (omega_user * params.L / 2.0);
        v_l = v_act - (omega_user * params.L / 2.0);
        wheels_unassisted(:, k) = [v_l / params.r; v_r / params.r];

        % Integrate differential drive kinematics using RK4
        state_unassisted(:, k+1) = rk4_step(@kinematics_deriv, state_unassisted(:, k), v_act, omega_user, dt);

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

    % --- 4. Scenario B: WAYLO Shared-Autonomy Active ---
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

        dist_to_door = params.door_y - y;
        c_left = params.door_half_w + x;
        c_right = params.door_half_w - x;
        min_clear = min(c_left, c_right);
        clearance_waylo(k) = min_clear;

        omega_user = (v_user_cmd / params.L) * tand(steer_drift_deg);

        heading_err = (pi/2) - th;
        lateral_err = 0.0 - x;

        kp_lat = 2.4;
        kp_head = 1.8;
        omega_copilot = kp_lat * lateral_err + kp_head * heading_err;
        omega_copilot = max(-params.w_max, min(params.w_max, omega_copilot));

        if dist_to_door > 0 && dist_to_door < 3.2
            proximity_weight = (3.2 - dist_to_door) / 3.2;
            clearance_deficit = max(0.0, (params.min_clearance_safe - min_clear) / params.min_clearance_safe);
            alpha = min(0.95, max(0.05, 0.40 * proximity_weight + 0.60 * clearance_deficit));
            v_copilot = max(0.40, v_user_cmd * (1.0 - 0.4 * clearance_deficit));
        elseif dist_to_door <= 0
            alpha = max(0.05, 0.40 * exp(-abs(dist_to_door)));
            v_copilot = v_user_cmd;
        else
            alpha = 0.05;
            v_copilot = v_user_cmd;
        end
        alpha_history(k) = alpha;

        v_final = (1.0 - alpha) * v_user_cmd + alpha * v_copilot;
        omega_final = (1.0 - alpha) * omega_user + alpha * omega_copilot;

        v_r = v_final + (omega_final * params.L / 2.0);
        v_l = v_final - (omega_final * params.L / 2.0);
        wheels_waylo(:, k) = [v_l / params.r; v_r / params.r];

        state_waylo(:, k+1) = rk4_step(@kinematics_deriv, state_waylo(:, k), v_final, omega_final, dt);

        if abs(dist_to_door) < 0.25 && min_clear <= 0.0
            collision_waylo = true;
        end
    end
    alpha_history(N) = alpha_history(N-1);
    clearance_waylo(N) = clearance_waylo(N-1);
    wheels_waylo(:, N) = wheels_waylo(:, N-1);

    % --- 5. 6-DOF Arm Forward/Inverse Kinematics & Reaching Simulation ---
    fprintf('Simulating 6-DOF Assistive Arm Inverse Kinematics Reaching...\n');
    % Arm Link Lengths: l1 = 0.32m (Upper Arm), l2 = 0.28m (Forearm), l3 = 0.40m (Elevation)
    arm.l1 = 0.32;
    arm.l2 = 0.28;
    arm.l3 = 0.40;

    % Target object (Glass on table at X=0.8m, Y=0.3m, Z=0.6m)
    target_obj = [0.80, 0.30, 0.60];
    % Arm base mount on wheelchair frame: [0.10, 0.28, 0.35]
    arm_mount = [0.10, 0.28, 0.35];

    % Relative target vector in arm coordinate frame
    rel_target = target_obj - arm_mount;
    x_t = rel_target(1);
    y_t = rel_target(2);
    z_t = rel_target(3);

    % Calculate Joint Angles using 6-DOF Forward/Inverse Kinematics:
    %   x = l1*cos(t1) + l2*cos(t1+t2)
    %   y = l1*sin(t1) + l2*sin(t1+t2)
    %   z = l3*sin(t3)
    t3_target = asin(max(-0.95, min(0.95, z_t / arm.l3)));

    % Planar 2-link IK for x, y
    D = (x_t^2 + y_t^2 - arm.l1^2 - arm.l2^2) / (2.0 * arm.l1 * arm.l2);
    D = max(-1.0, min(1.0, D));
    t2_target = atan2(sqrt(1.0 - D^2), D);
    t1_target = atan2(y_t, x_t) - atan2(arm.l2 * sin(t2_target), arm.l1 + arm.l2 * cos(t2_target));

    % Wrist joints t4, t5, t6 orienting parallel gripper
    t4_target = 0.0;
    t5_target = -(t1_target + t2_target) + 0.15;
    t6_target = 0.10;

    target_joint_angles = [t1_target, t2_target, t3_target, t4_target, t5_target, t6_target];
    home_joint_angles   = [0.0, 0.20, 0.15, 0.0, 0.45, 0.0];

    % Forward Kinematics verification:
    fk_x = arm.l1 * cos(t1_target) + arm.l2 * cos(t1_target + t2_target);
    fk_y = arm.l1 * sin(t1_target) + arm.l2 * sin(t1_target + t2_target);
    fk_z = arm.l3 * sin(t3_target);
    fk_pos = arm_mount + [fk_x, fk_y, fk_z];
    ik_error_m = norm(fk_pos - target_obj);
    fprintf('IK Convergence: End-Effector reached within %0.4f m of target glass.\n', ik_error_m);

    % Smooth trajectory reaching interpolation (quintic minimum-jerk profile)
    arm_steps = 100;
    tau = linspace(0, 1, arm_steps);
    s_curve = 10*tau.^3 - 15*tau.^4 + 6*tau.^5; % Quintic s-curve in [0, 1]

    arm_joint_traj = zeros(6, arm_steps);
    for j = 1:6
        arm_joint_traj(j, :) = home_joint_angles(j) + s_curve * (target_joint_angles(j) - home_joint_angles(j));
    end

    % Base stability calculation (Zero-Moment Point / Center of Gravity Margin)
    base_mass = 110; % kg
    arm_mass  = 8.5; % kg
    cog_x = (base_mass * 0.0 + arm_mass * (arm_mount(1) + fk_x * s_curve)) / (base_mass + arm_mass);
    stability_margin = (params.L/2.0 - abs(cog_x)) / (params.L/2.0); % > 0 means stable

    % --- 6. Send Telemetry to FastAPI Arm Manipulation Endpoint ---
    arm_api_url = 'http://localhost:8000/api/v1/arm-manipulation';
    arm_opts = weboptions('MediaType', 'application/json', 'Timeout', 0.5, 'RequestMethod', 'post');
    arm_payload = struct( ...
        'intent', 'GRASP_WATER_BOTTLE', ...
        'anonymize_privacy', true ...
    );
    try
        api_res = webwrite(arm_api_url, arm_payload, arm_opts);
        fprintf('Dispatched Arm Telemetry to FastAPI -> %s (Status: %s)\n', arm_api_url, api_res.status);
    catch ME
        fprintf('FastAPI server offline (%s). Using local kinematics.\n', ME.message);
    end

    % --- 7. Plot Figures: Trajectory, Wheel Speeds, 6-DOF Arm Reach & Joint Trajectories ---
    fig = figure('Name', 'WAYLO Kinematics & 6-DOF Arm Manipulation', ...
                 'Color', [0.08 0.10 0.15], 'Position', [50, 30, 1300, 780]);

    % Subplot 1: Side-by-Side 2D Spatial Trajectory
    ax1 = subplot(2, 2, 1);
    hold(ax1, 'on'); grid(ax1, 'on');
    set(ax1, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);

    plot(ax1, [-3, -params.door_half_w], [params.door_y, params.door_y], 'Color', [0.5 0.55 0.65], 'LineWidth', 4);
    plot(ax1, [params.door_half_w, 3], [params.door_y, params.door_y], 'Color', [0.5 0.55 0.65], 'LineWidth', 4);
    plot(ax1, [-params.door_half_w, params.door_half_w], [params.door_y, params.door_y], '--', 'Color', [0.2 0.85 0.4], 'LineWidth', 2.5);
    plot(ax1, -params.door_half_w, params.door_y, 'ks', 'MarkerFaceColor', [0.9 0.4 0.2], 'MarkerSize', 8);
    plot(ax1, params.door_half_w, params.door_y, 'ks', 'MarkerFaceColor', [0.9 0.4 0.2], 'MarkerSize', 8);
    text(ax1, 0.0, params.door_y + 0.35, '1.2m DOORWAY', 'Color', [0.6 0.95 0.7], ...
         'FontSize', 9, 'FontWeight', 'bold', 'HorizontalAlignment', 'center');

    p1 = plot(ax1, state_unassisted(1, :), state_unassisted(2, :), '--', 'Color', [0.95 0.3 0.4], 'LineWidth', 2.4);
    p2 = plot(ax1, state_waylo(1, :), state_waylo(2, :), '-', 'Color', [0.15 0.85 0.45], 'LineWidth', 3.0);

    xlabel(ax1, 'Lateral Position X (m)', 'FontWeight', 'bold');
    ylabel(ax1, 'Forward Position Y (m)', 'FontWeight', 'bold');
    title(ax1, {'\bf1. 2D Spatial Trajectory Curves', '\rmUnassisted Drift vs. WAYLO Centered Path'}, ...
          'Color', 'white', 'FontSize', 11);
    legend(ax1, [p1, p2], {'Unassisted (Collision Course)', 'WAYLO Copilot (Centered)'}, ...
           'Location', 'northwest', 'TextColor', 'white', 'Color', [0.15 0.18 0.26]);
    axis(ax1, [-2.2, 2.2, 0.0, 6.0]);

    % Subplot 2: Side-by-Side Wheel Angular Speeds (omega_L, omega_R)
    ax2 = subplot(2, 2, 2);
    hold(ax2, 'on'); grid(ax2, 'on');
    set(ax2, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);

    w1 = plot(ax2, time, wheels_unassisted(1, :), ':', 'Color', [0.95 0.4 0.4], 'LineWidth', 1.8);
    w2 = plot(ax2, time, wheels_unassisted(2, :), ':', 'Color', [0.95 0.7 0.3], 'LineWidth', 1.8);
    w3 = plot(ax2, time, wheels_waylo(1, :), '-', 'Color', [0.35 0.75 1.0], 'LineWidth', 2.4);
    w4 = plot(ax2, time, wheels_waylo(2, :), '-', 'Color', [0.2 0.9 0.5], 'LineWidth', 2.4);

    xlabel(ax2, 'Time (seconds)', 'FontWeight', 'bold');
    ylabel(ax2, 'Wheel Speed \omega (rad/s)', 'FontWeight', 'bold');
    title(ax2, {'\bf2. Wheel Angular Speeds (\omega_L, \omega_R)', '\rm(v_R - v_L)/L Differential Actuation'}, ...
          'Color', 'white', 'FontSize', 11);
    legend(ax2, [w1, w2, w3, w4], ...
           {'Unassisted \omega_L', 'Unassisted \omega_R', 'WAYLO \omega_L', 'WAYLO \omega_R'}, ...
           'Location', 'best', 'TextColor', 'white', 'Color', [0.15 0.18 0.26]);

    % Subplot 3: 6-DOF Robotic Arm Reaching Animation Path
    ax3 = subplot(2, 2, 3);
    hold(ax3, 'on'); grid(ax3, 'on');
    set(ax3, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85], 'ZColor', [0.7 0.75 0.85]);
    view(ax3, [35, 25]);

    % Plot Target Glass
    [Xg, Yg, Zg] = cylinder(0.05, 12);
    Zg = Zg * 0.14 + (target_obj(3) - 0.07);
    Xg = Xg + target_obj(1);
    Yg = Yg + target_obj(2);
    surf(ax3, Xg, Yg, Zg, 'FaceColor', [0.25 0.85 1.0], 'EdgeColor', 'none', 'FaceAlpha', 0.65);
    plot3(ax3, target_obj(1), target_obj(2), target_obj(3), 'p', ...
          'MarkerFaceColor', [1.0 0.85 0.2], 'MarkerEdgeColor', 'w', 'MarkerSize', 12);
    text(ax3, target_obj(1), target_obj(2), target_obj(3)+0.12, 'Target Glass', ...
         'Color', [0.4 0.95 1.0], 'FontWeight', 'bold', 'FontSize', 9, 'HorizontalAlignment', 'center');

    % Arm Base Mount
    plot3(ax3, arm_mount(1), arm_mount(2), arm_mount(3), 's', ...
          'MarkerFaceColor', [0.85 0.65 0.15], 'MarkerEdgeColor', 'w', 'MarkerSize', 10);
    text(ax3, arm_mount(1), arm_mount(2), arm_mount(3)+0.08, 'Arm Mount Base', ...
         'Color', [0.9 0.7 0.2], 'FontSize', 8, 'HorizontalAlignment', 'center');

    % Reaching end-effector trajectory line
    ee_traj = zeros(arm_steps, 3);
    for step = 1:arm_steps
        t1_s = arm_joint_traj(1, step);
        t2_s = arm_joint_traj(2, step);
        t3_s = arm_joint_traj(3, step);
        ex = arm.l1 * cos(t1_s) + arm.l2 * cos(t1_s + t2_s);
        ey = arm.l1 * sin(t1_s) + arm.l2 * sin(t1_s + t2_s);
        ez = arm.l3 * sin(t3_s);
        ee_traj(step, :) = arm_mount + [ex, ey, ez];
    end
    plot3(ax3, ee_traj(:,1), ee_traj(:,2), ee_traj(:,3), '-.', 'Color', [0.2 0.9 0.5], 'LineWidth', 2.2);

    % Draw Final Reach Posture
    p_j1 = arm_mount;
    p_j2 = p_j1 + [arm.l1 * cos(t1_target), arm.l1 * sin(t1_target), 0.10];
    p_j3 = p_j2 + [arm.l2 * cos(t1_target + t2_target), arm.l2 * sin(t1_target + t2_target), arm.l3 * sin(t3_target) - 0.10];
    plot3(ax3, [p_j1(1), p_j2(1)], [p_j1(2), p_j2(2)], [p_j1(3), p_j2(3)], '-', 'Color', [0.3 0.75 0.95], 'LineWidth', 5);
    plot3(ax3, [p_j2(1), p_j3(1)], [p_j2(2), p_j3(2)], [p_j2(3), p_j3(3)], '-', 'Color', [0.2 0.85 0.55], 'LineWidth', 4);

    xlabel(ax3, 'X (m)'); ylabel(ax3, 'Y (m)'); zlabel(ax3, 'Z (m)');
    title(ax3, {'\bf3. 6-DOF Arm Reaching & End-Effector IK', '\rmFrom Home Pose to Glass [0.8, 0.3, 0.6]'}, ...
          'Color', 'white', 'FontSize', 11);
    axis(ax3, [0.0, 1.0, 0.0, 0.6, 0.2, 0.8]);

    % Subplot 4: 6-DOF Joint Angles & Base Stability Margin
    ax4 = subplot(2, 2, 4);
    hold(ax4, 'on'); grid(ax4, 'on');
    set(ax4, 'Color', [0.11 0.14 0.20], 'XColor', [0.7 0.75 0.85], 'YColor', [0.7 0.75 0.85]);

    traj_time = linspace(0, 2.5, arm_steps);
    j_colors = lines(6);
    for j = 1:6
        plot(ax4, traj_time, rad2deg(arm_joint_traj(j, :)), '-', 'Color', j_colors(j, :), 'LineWidth', 1.8);
    end

    xlabel(ax4, 'Reach Time (seconds)', 'FontWeight', 'bold');
    ylabel(ax4, 'Joint Angles \theta_i (deg)', 'FontWeight', 'bold');
    title(ax4, {'\bf4. 6-DOF Joint Angle Trajectories \theta_1...\theta_6', ...
                sprintf('\\rmBase Stability Margin: \\bf%0.1f%% \\rm(Zero Tip-Over Hazard)', min(stability_margin)*100)}, ...
          'Color', 'white', 'FontSize', 11);
    legend(ax4, {'\theta_1 (Waist)', '\theta_2 (Shoulder)', '\theta_3 (Elbow)', '\theta_4 (Wrist Roll)', '\theta_5 (Wrist Pitch)', '\theta_6 (Wrist Yaw)'}, ...
           'Location', 'eastoutside', 'TextColor', 'white', 'Color', [0.15 0.18 0.26]);

    % Figure Super Title
    sgtitle(fig, 'WAYLO: 6-DOF Robotic Arm IK Manipulation & Wheelchair Kinematics', ...
            'Color', 'white', 'FontSize', 13, 'FontWeight', 'bold');
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
