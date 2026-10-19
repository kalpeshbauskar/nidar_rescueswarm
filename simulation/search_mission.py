#!/usr/bin/env python3
"""Bounded SITL-only takeoff, 2 m square, return and land verification."""
import csv, json, math, os, time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from px4_msgs.msg import (VehicleLocalPosition, VehicleStatus, VehicleLandDetected,
    VehicleCommandAck, VehicleCommand, OffboardControlMode, TrajectorySetpoint)

if os.environ.get('ROS_DOMAIN_ID') != '87':
    raise SystemExit('This check is restricted to simulation ROS domain 87.')

class Check(Node):
    def __init__(self):
        super().__init__('nidar_search_mission')
        self.pos=self.status=self.land=None
        self.pos_at=0.; self.start=time.monotonic(); self.phase='WAIT'; self.since=self.start
        self.last_cmd=0.; self.index=0; self.stable=None; self.points=[]; self.done=False; self.success=False
        self.max_alt=0.; self.reached=[]; self.last_log=0.; self.origin=None; self.error=None
        q=qos_profile_sensor_data
        self.create_subscription(VehicleLocalPosition,'/fmu/out/vehicle_local_position_v1',self.position,q)
        self.create_subscription(VehicleStatus,'/fmu/out/vehicle_status_v4',lambda m:setattr(self,'status',m),q)
        self.create_subscription(VehicleLandDetected,'/fmu/out/vehicle_land_detected',lambda m:setattr(self,'land',m),q)
        self.create_subscription(VehicleCommandAck,'/fmu/out/vehicle_command_ack_v1',self.ack,q)
        self.mode=self.create_publisher(OffboardControlMode,'/fmu/in/offboard_control_mode',10)
        self.sp=self.create_publisher(TrajectorySetpoint,'/fmu/in/trajectory_setpoint',10)
        self.cmd=self.create_publisher(VehicleCommand,'/fmu/in/vehicle_command',10)
        self.file=open(Path(__file__).parent/'logs/search-telemetry.csv','w')
        self.csv=csv.writer(self.file); self.csv.writerow(['wall_seconds','phase','waypoint','north','east','down','armed','nav_state'])
        self.create_timer(.1,self.tick)
    def position(self,m):self.pos=m;self.pos_at=time.monotonic()
    def ack(self,m):
        print('ACK',m.command,m.result,flush=True)
    def stamp(self):return self.get_clock().now().nanoseconds//1000
    def command(self,command,p1=0.,p2=0.):
        m=VehicleCommand();m.timestamp=self.stamp();m.command=command;m.param1=float(p1);m.param2=float(p2)
        m.target_system=1;m.target_component=1;m.source_system=1;m.source_component=191;m.from_external=True
        self.cmd.publish(m);self.last_cmd=time.monotonic()
    def change(self,p):
        self.phase=p;self.since=time.monotonic();print('PHASE',p,flush=True)
    def tick(self):
        now=time.monotonic();p=self.pos;s=self.status
        if now-self.start>1800 and self.phase!='LAND':
            self.error='flight timeout';self.change('LAND')
        if p and s:
            self.csv.writerow([round(now-self.start,2),self.phase,self.index,p.x,p.y,p.z,s.arming_state,s.nav_state]);self.file.flush()
            if self.origin:self.max_alt=max(self.max_alt,self.origin[2]-p.z)
            if now-self.last_log>3:
                print(self.phase,self.index,'position',round(p.x,2),round(p.y,2),round(p.z,2),'armed',s.arming_state,'mode',s.nav_state,flush=True);self.last_log=now
        if self.phase=='WAIT':
            if p and s and p.xy_valid and p.z_valid and now-self.pos_at<1:
                self.origin=(p.x,p.y,p.z);x,y,z=self.origin
                # Gazebo world is ENU: PX4 North=world Y, East=world X.
                world_xy=[(40,40),(80,130),(140,60),(150,-60),(100,-140),(20,-100),(-90,-140),(-120,-100),(-150,40),(-40,90)]
                self.points=[(x,y,z-5)]+[(north,east,z-5) for east,north in world_xy]+[(x,y,z-5)]
                self.change('WARMUP')
            elif now-self.start>30:self.error='no valid position';self.done=True
            return
        if self.phase=='LAND':
            if now-self.last_cmd>2:self.command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
            if self.land and self.land.landed and s and s.arming_state!=VehicleStatus.ARMING_STATE_ARMED:
                self.success=self.error is None and len(self.reached)==len(self.points);self.done=True
                print('LANDED AND DISARMED',self.success,flush=True)
            if now-self.since>60:self.error='landing timeout';self.done=True
            return
        if not p or now-self.pos_at>2 or not p.xy_valid or not p.z_valid:
            self.error='position unavailable';self.change('LAND');return
        m=OffboardControlMode();m.timestamp=self.stamp();m.position=True;self.mode.publish(m)
        t=TrajectorySetpoint();t.timestamp=self.stamp();t.position=list(self.points[self.index]);t.velocity=[math.nan]*3;t.acceleration=[math.nan]*3;t.yaw=0.;t.yawspeed=math.nan;self.sp.publish(t)
        if self.phase=='WARMUP' and now-self.since>2:self.change('OFFBOARD')
        if self.phase=='OFFBOARD':
            if s.nav_state==VehicleStatus.NAVIGATION_STATE_OFFBOARD:self.change('ARM')
            elif now-self.last_cmd>2:self.command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE,1,6)
        elif self.phase=='ARM':
            if s.arming_state==VehicleStatus.ARMING_STATE_ARMED:self.change('FLY')
            elif now-self.last_cmd>2:self.command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,1)
        elif self.phase=='FLY':
            if s.nav_state!=VehicleStatus.NAVIGATION_STATE_OFFBOARD:
                self.error='offboard lost';self.change('LAND');return
            target=self.points[self.index]
            distance=math.sqrt(sum((a-b)**2 for a,b in zip((p.x,p.y,p.z),target)))
            speed=math.sqrt(p.vx*p.vx+p.vy*p.vy+p.vz*p.vz)
            if distance<.4 and speed<.35:
                if self.stable is None:self.stable=now
                if now-self.stable>3:
                    self.reached.append({'index':self.index,'distance':distance});print('REACHED',self.index,flush=True)
                    self.index+=1;self.stable=None
                    if self.index==len(self.points):self.change('LAND')
            else:self.stable=None

def main():
    rclpy.init();n=Check()
    try:
        while not n.done:rclpy.spin_once(n,timeout_sec=.2)
    except KeyboardInterrupt:
        n.error='interrupted';n.command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
    finally:
        result={'success':n.success,'error':n.error,'max_altitude_m':n.max_alt,'reached':n.reached,'duration_s':time.monotonic()-n.start}
        (Path(__file__).parent/'logs/search-result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result),flush=True);n.file.close();n.destroy_node();rclpy.shutdown()
    raise SystemExit(0 if n.success else 1)
if __name__=='__main__':main()
