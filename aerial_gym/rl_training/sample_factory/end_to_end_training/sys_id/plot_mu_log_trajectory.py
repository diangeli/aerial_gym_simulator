import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from scipy.spatial.transform import Rotation as R
from scipy.interpolate import interp1d

if __name__ == "__main__":
    
    # PX4 uses NED coordinate system, while the simulator uses ENU coordinate system
    # The transformation matrix is the following:
    transformation_1 = np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]])
    transformation_2 = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    
    exp_name = "ete_seed_56_2025-1-15-14-06"
    
    # Load data
    pos_lin_vel_data = pd.read_csv("./ulogs/" + exp_name + "/" + exp_name + "_vehicle_local_position_0.csv")
    att_data = pd.read_csv("./ulogs/" + exp_name + "/" + exp_name + "_vehicle_attitude_0.csv")
    ang_vel_data = pd.read_csv("./ulogs/" + exp_name + "/" + exp_name + "_vehicle_angular_velocity_0.csv")
    esc_rpm_data = pd.read_csv("./ulogs/" + exp_name + "/" + exp_name + "_esc_status_0.csv")
    
    # Extract data and remove 0 values from rpm (publishing issue)
    pos = np.array([pos_lin_vel_data["x"].tolist(),pos_lin_vel_data["y"].tolist(),pos_lin_vel_data["z"].tolist()])
    lin_vel = np.array([pos_lin_vel_data["vx"].tolist(),pos_lin_vel_data["vy"].tolist(),pos_lin_vel_data["vz"].tolist()])
    q_att = np.array([att_data["q[1]"].tolist(),att_data["q[2]"].tolist(),att_data["q[3]"].tolist(),att_data["q[0]"].tolist()])
    ang_vel = np.array([ang_vel_data["xyz[0]"].tolist(),ang_vel_data["xyz[1]"].tolist(),ang_vel_data["xyz[2]"].tolist()])
    rpm0 = np.array([x for x in esc_rpm_data["esc[0].esc_rpm"].tolist() if x != 0])
    rpm1 = np.array([x for x in esc_rpm_data["esc[1].esc_rpm"].tolist() if x != 0])
    rpm2 = np.array([x for x in esc_rpm_data["esc[2].esc_rpm"].tolist() if x != 0])
    rpm3 = np.array([x for x in esc_rpm_data["esc[3].esc_rpm"].tolist() if x != 0])
    
    # Transform data
    pos_enu = transformation_1 @ transformation_2 @ pos
    lin_vel_enu = transformation_1 @ transformation_2 @ lin_vel
    
    r = R.from_quat(q_att.T)
    r_enu = R.from_matrix(transformation_1 @ (transformation_2 @ r.as_matrix()) @ transformation_1.T)
    ang_enu = r_enu.as_euler("xyz", degrees=True)
    q_att_enu = r_enu.as_quat().T
    
    ang_vel_enu = transformation_1 @ ang_vel
    
    # Get time points
    uorb_timestep_size = 1/1e6 # one micro second
    
    time_points_pos_vel = np.array((pos_lin_vel_data["timestamp"].iloc[:] - pos_lin_vel_data["timestamp"].iloc[0]))*uorb_timestep_size
    time_points_att = np.array((att_data["timestamp"].iloc[:] - att_data["timestamp"].iloc[0]))*uorb_timestep_size
    time_points_ang_vel = np.array((ang_vel_data["timestamp"].iloc[:] - ang_vel_data["timestamp"].iloc[0]))*uorb_timestep_size
    time_points_rpm = np.array((esc_rpm_data["timestamp"].iloc[:] - esc_rpm_data["timestamp"].iloc[0]))*uorb_timestep_size
    time_points_rpm0 = np.array([time_points_rpm[i] for i in range(len(time_points_rpm)) if esc_rpm_data["esc[0].esc_rpm"].iloc[i] != 0])
    time_points_rpm1 = np.array([time_points_rpm[i] for i in range(len(time_points_rpm)) if esc_rpm_data["esc[1].esc_rpm"].iloc[i] != 0])
    time_points_rpm2 = np.array([time_points_rpm[i] for i in range(len(time_points_rpm)) if esc_rpm_data["esc[2].esc_rpm"].iloc[i] != 0])
    time_points_rpm3 = np.array([time_points_rpm[i] for i in range(len(time_points_rpm)) if esc_rpm_data["esc[3].esc_rpm"].iloc[i] != 0])
    
    # Interpolate data
    f_pos = interp1d(time_points_pos_vel, pos_enu, axis=1)
    f_lin_vel = interp1d(time_points_pos_vel, lin_vel_enu, axis=1)
    f_q_att = interp1d(time_points_att, q_att_enu, axis=1)
    f_ang_vel = interp1d(time_points_ang_vel, ang_vel_enu, axis=1)
    f_rpm0 = interp1d(time_points_rpm0, rpm0)
    f_rpm1 = interp1d(time_points_rpm1, rpm1)
    f_rpm2 = interp1d(time_points_rpm2, rpm2)
    f_rpm3 = interp1d(time_points_rpm3, rpm3)
    
    sim_dt = 0.01
    T_start = max([time_points_rpm0[0], time_points_rpm1[0], time_points_rpm2[0], time_points_rpm3[0]])
    T_end = min([time_points_rpm0[-1], time_points_rpm1[-1], time_points_rpm2[-1], time_points_rpm3[-1]])
    n_points = int((T_end - T_start)/sim_dt)
    
    time_points = np.linspace(T_start, T_end, n_points)
    
    pos_enu_interp = f_pos(time_points)
    lin_vel_enu_interp = f_lin_vel(time_points)
    ang_enu_interp = R.from_quat(f_q_att(time_points).T).as_euler("xyz", degrees=True)
    ang_vel_enu_interp = f_ang_vel(time_points)
    rpm0_interp = f_rpm0(time_points)
    rpm1_interp = f_rpm1(time_points)
    rpm2_interp = f_rpm2(time_points)
    rpm3_interp = f_rpm3(time_points)
    
    k_t = 0.00001286412
    f_0_interp = k_t * (rpm0_interp/60)**2
    f_1_interp = k_t * (rpm1_interp/60)**2
    f_2_interp = k_t * (rpm2_interp/60)**2
    f_3_interp = k_t * (rpm3_interp/60)**2
    
    f_interp = np.array([f_0_interp, f_1_interp, f_2_interp, f_3_interp])
    
    setpoint_positions = np.array([[0.,0.,1.],[-.7,-.7,1.],[.7,-.7,1.],[.7,.7,1.],[-.7,.7,1.],[-.7,-.7,1.],[0.,0.,1.]])
    
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot(pos_enu_interp[0], pos_enu_interp[1], pos_enu_interp[2])
    ax.scatter(setpoint_positions[:,0], setpoint_positions[:,1], setpoint_positions[:,2], c='r', marker='o')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    
    plt.savefig("3d_traj.pdf")