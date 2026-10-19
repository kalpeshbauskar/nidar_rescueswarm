import re
with open('simulation/dual/mission.py') as f:
    text = f.read()
text = text.replace('self.swarm_pub.publish(msg); self.seq += 1', 'self.swarm_pub.publish(msg); self.seq += 1\n   if self.seq % 10 == 0: print("Published state", self.i, flush=True)')
with open('simulation/dual/mission.py', 'w') as f:
    f.write(text)
