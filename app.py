import sys
import math
import random
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QSlider, QLabel, QPushButton, QCheckBox,
                               QTabWidget, QComboBox)
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (QPainter, QColor, QLinearGradient, QPen, QPainterPath, 
                           QPixmap, QPolygonF)

class FoodOrb:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 8
        self.pulse = 0
        self.eaten = False

    def update(self, global_speed):
        self.pulse += 0.1 * global_speed

    def draw(self, painter):
        glow_size = self.radius + math.sin(self.pulse) * 3
        painter.setBrush(QColor(255, 255, 150, 100))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(self.x, self.y), glow_size, glow_size)
        painter.setBrush(QColor(255, 255, 200))
        painter.drawEllipse(QPointF(self.x, self.y), self.radius, self.radius)

class Particle:
    def __init__(self, x, y, vx, vy, color, lifespan, gravity, p_type="spark"):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = 1.0
        self.lifespan = lifespan
        self.color = color
        self.size = random.uniform(1.5, 4.0)
        self.gravity = gravity
        self.p_type = p_type
        self.wobble_phase = random.uniform(0, math.pi * 2)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.p_type == "bubble":
            self.vy -= 0.1
            self.vx += math.sin(self.life * 10 + self.wobble_phase) * 0.2
            self.vx *= 0.9
        elif self.p_type == "ink":
            self.vx *= 0.98
            self.vy *= 0.98
            self.size += 0.5 # Ink expands
        else:
            self.vx *= 0.95
            self.vy *= 0.95
            self.vy += self.gravity
        self.life -= self.lifespan

    def draw(self, painter):
        if self.life > 0:
            c = QColor(self.color)
            c.setAlphaF(self.life)
            if self.p_type == "bubble":
                painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
                painter.setBrush(Qt.NoBrush)
            else:
                painter.setBrush(c)
                painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(self.x, self.y), self.size, self.size)

class KelpStrand:
    def __init__(self, x, bounds_h, segments=20, length=15):
        self.segments = segments
        self.segment_length = length
        self.points = [QPointF(x, bounds_h - i * length) for i in range(segments)]
        self.old_points = [QPointF(x, bounds_h - i * length) for i in range(segments)]
        self.hue = random.uniform(0.25, 0.4)

    def update(self, wind_x, flow_y, bounds_h):
        self.points[0].setX(self.points[0].x())
        self.points[0].setY(bounds_h)

        for i in range(1, self.segments):
            p = self.points[i]
            old_p = self.old_points[i]
            vx = (p.x() - old_p.x()) * 0.95 + wind_x
            vy = (p.y() - old_p.y()) * 0.95 + flow_y * 0.5
            self.old_points[i].setX(p.x())
            self.old_points[i].setY(p.y())
            p.setX(p.x() + vx)
            p.setY(p.y() + vy + 0.2)

        for _ in range(3):
            for i in range(self.segments - 1):
                p1 = self.points[i]
                p2 = self.points[i + 1]
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()
                distance = math.hypot(dx, dy)
                if distance == 0: distance = 0.0001
                difference = (self.segment_length - distance) / distance
                offset_x = dx * difference * 0.5
                offset_y = dy * difference * 0.5
                if i != 0:
                    p1.setX(p1.x() - offset_x)
                    p1.setY(p1.y() - offset_y)
                p2.setX(p2.x() + offset_x)
                p2.setY(p2.y() + offset_y)

    def draw(self, painter):
        path = QPainterPath()
        path.moveTo(self.points[0])
        for i in range(len(self.points)-1):
            p1 = self.points[i]
            p2 = self.points[i+1]
            mid = QPointF((p1.x() + p2.x())/2, (p1.y() + p2.y())/2)
            path.quadTo(p1, mid)
        path.lineTo(self.points[-1])
        color = QColor.fromHslF(self.hue, 0.6, 0.25, 0.8)
        pen = QPen(color, 4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)

class Appendage:
    def __init__(self, anchor_idx, segments, length, app_type, is_lure=False):
        self.anchor_idx = anchor_idx
        self.segments = segments
        self.segment_length = length
        self.app_type = app_type
        self.is_lure = is_lure
        self.points = []
        self.old_points = []

    def init_points(self, start_pos):
        self.points = [QPointF(start_pos.x(), start_pos.y()) for _ in range(self.segments)]
        self.old_points = [QPointF(start_pos.x(), start_pos.y()) for _ in range(self.segments)]

    def update(self, anchor_pos, anchor_vel, bounds_w, bounds_h, gravity, friction, wind_x, wind_y, mouse_pos, mouse_force, stiffness, flow_x, flow_y):
        if not self.points:
            self.init_points(anchor_pos)

        self.points[0].setX(anchor_pos.x())
        self.points[0].setY(anchor_pos.y())

        for i in range(1, self.segments):
            p = self.points[i]
            old_p = self.old_points[i]
            vx = (p.x() - old_p.x()) * friction + anchor_vel.x() * 0.5
            vy = (p.y() - old_p.y()) * friction + anchor_vel.y() * 0.5
            self.old_points[i].setX(p.x())
            self.old_points[i].setY(p.y())
            p.setX(p.x() + vx + wind_x + flow_x)
            p.setY(p.y() + vy + gravity + wind_y + flow_y)

            if mouse_force == 2:
                dx = p.x() - mouse_pos.x()
                dy = p.y() - mouse_pos.y()
                dist_sq = dx*dx + dy*dy
                if dist_sq < 40000:
                    dist = math.sqrt(dist_sq) + 0.001
                    tx = -dy / dist
                    ty = dx / dist
                    force = (1 - dist / 200) * 2.0
                    p.setX(p.x() + tx * force * 4.0)
                    p.setY(p.y() + ty * force * 4.0)
                    p.setX(p.x() - (dx / dist) * force * 0.3)
                    p.setY(p.y() - (dy / dist) * force * 0.3)
            elif mouse_force != 0:
                dx = p.x() - mouse_pos.x()
                dy = p.y() - mouse_pos.y()
                dist_sq = dx*dx + dy*dy
                if dist_sq < 30000:
                    dist = math.sqrt(dist_sq) + 0.001
                    force = (1 - dist / 173) * mouse_force * 2.0
                    p.setX(p.x() + (dx / dist) * force)
                    p.setY(p.y() + (dy / dist) * force)

        for _ in range(stiffness):
            for i in range(self.segments - 1):
                p1 = self.points[i]
                p2 = self.points[i + 1]
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()
                distance = math.hypot(dx, dy)
                if distance == 0: distance = 0.0001
                difference = (self.segment_length - distance) / distance
                offset_x = dx * difference * 0.5
                offset_y = dy * difference * 0.5
                if i != 0:
                    p1.setX(p1.x() - offset_x)
                    p1.setY(p1.y() - offset_y)
                p2.setX(p2.x() + offset_x)
                p2.setY(p2.y() + offset_y)

        for i in range(1, self.segments):
            p = self.points[i]
            if p.x() < 0: p.setX(0)
            if p.x() > bounds_w: p.setX(bounds_w)
            if p.y() < 0: p.setY(0)
            if p.y() > bounds_h: p.setY(bounds_h)

    def draw(self, painter, color, wireframe, time_offset, global_speed):
        if len(self.points) < 2: return
        
        if self.app_type == 1:
            p1 = self.points[0]
            p2 = self.points[-1]
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(QPolygonF([p1, p2, QPointF(p1.x(), p1.y())]))
            return
            
        if self.app_type == 2:
            path = QPainterPath()
            p1 = self.points[0]
            p2 = self.points[-1]
            mid = QPointF((p1.x()+p2.x())/2, (p1.y()+p2.y())/2)
            wobble = math.sin(time_offset * global_speed * 2) * 5
            path.moveTo(p1)
            path.quadTo(QPointF(mid.x()+wobble, mid.y()+wobble), p2)
            painter.setPen(QPen(color, 2))
            painter.drawPath(path)
            return

        path = QPainterPath()
        path.moveTo(self.points[0])
        for i in range(len(self.points)-1):
            p1 = self.points[i]
            p2 = self.points[i+1]
            mid = QPointF((p1.x() + p2.x())/2, (p1.y() + p2.y())/2)
            path.quadTo(p1, mid)
        path.lineTo(self.points[-1])
        
        if wireframe:
            pen = QPen(QColor(255, 255, 255, 100))
            pen.setStyle(Qt.DashLine)
        else:
            pen = QPen(color)
            pen.setWidthF(2.5)
            pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Anglerfish Lure
        if self.is_lure:
            tip = self.points[-1]
            pulse = 1.0 + math.sin(time_offset * global_speed * 3) * 0.3
            painter.setBrush(QColor(255, 255, 150, 150))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(tip, 6 * pulse, 6 * pulse)
            painter.setBrush(QColor(255, 255, 200))
            painter.drawEllipse(tip, 3, 3)


class ProceduralCreature:
    def __init__(self, start_x, start_y, segments=20, segment_length=15, dna=None):
        self.segments = segments
        self.segment_length = segment_length
        self.points = [QPointF(start_x, start_y) for _ in range(segments)]
        self.old_points = [QPointF(start_x, start_y) for _ in range(segments)]
        
        self.head_x = start_x
        self.head_y = start_y
        self.wander_target = QPointF(start_x, start_y)
        self.wander_angle = random.uniform(0, math.pi * 2)
        
        if dna:
            self.base_hue = dna['hue']
            self.generation = dna['generation'] + 1
        else:
            self.base_hue = random.random()
            self.generation = 1
            
        self.appendages = []
        self.time_offset = random.uniform(0, 100)
        self.swim_phase = 0.0
        
        self.age = 0
        self.max_age = random.randint(500, 1500)
        self.size_mult = 1.0
        self.alive = True
        self.food_eaten = 0
        
        self.is_predator = random.random() < 0.15
        if self.is_predator:
            self.base_hue = 0.0
            
        self.ink_cooldown = 0
        self.particles_to_emit = []

    def get_palette_colors(self, t, settings):
        s = settings
        pal = s['palette']
        h1 = (self.base_hue + s['hue_shift']) % 1.0
        h2 = (h1 + s['grad_spread']) % 1.0
        
        if pal == 0:
            c1 = QColor.fromHslF(h1, s['color_sat'], s['color_light'])
            c2 = QColor.fromHslF(h2, s['color_sat'], s['color_light'] * 0.8)
        elif pal == 1:
            c1 = QColor.fromHslF(0.05, 1.0, 0.2 + t * 0.4)
            c2 = QColor.fromHslF(0.12, 1.0, 0.2 + t * 0.5)
        elif pal == 2:
            c1 = QColor.fromHslF(0.35, 1.0, 0.3 + t * 0.3)
            c2 = QColor.fromHslF(0.45, 1.0, 0.3 + t * 0.4)
        elif pal == 3:
            c1 = QColor.fromHslF((h1 + t * 0.5) % 1.0, 0.9, 0.6)
            c2 = QColor.fromHslF((h1 + t * 0.6) % 1.0, 0.9, 0.5)
        elif pal == 4:
            c1 = QColor.fromHslF(0, 0, 0.3 + t * 0.5)
            c2 = QColor.fromHslF(0, 0, 0.2 + t * 0.4)
        else:
            c1 = QColor.fromHslF(h1, s['color_sat'], s['color_light'])
            c2 = QColor.fromHslF(h2, s['color_sat'], s['color_light'] * 0.8)
            
        if self.is_predator:
            c1 = QColor(max(c1.red(), 150), c1.green() // 2, c1.blue() // 2)
            c2 = QColor(max(c2.red(), 150), c2.green() // 2, c2.blue() // 2)
            
        return c1, c2

    def update(self, target_x, target_y, bounds_w, bounds_h, settings, all_creatures, food_orbs, flow_time):
        if not self.alive: return None
        
        s = settings
        self.swim_phase += s['swim_freq'] * 0.05 * s['global_speed']
        self.age += s['global_speed']
        self.ink_cooldown -= s['global_speed']
        
        if s['lifecycle']:
            life_t = self.age / self.max_age
            if life_t < 0.2: self.size_mult = life_t / 0.2
            elif life_t > 0.8: self.size_mult = max(0.1, 1.0 - ((life_t - 0.8) / 0.2))
            else: self.size_mult = 1.0
            if life_t >= 1.0:
                self.alive = False
                return None
        else:
            self.size_mult = 1.0
            
        # Jet Propulsion Body Pulse
        current_seg_len = s['seg_length']
        if s['pulse_size'] > 0:
            pulse = 1.0 + math.sin(self.time_offset * s['global_speed'] * s['swim_freq']) * s['pulse_size']
            current_seg_len *= pulse
            
        self.segment_length = current_seg_len * self.size_mult
        
        closest_food = None
        closest_food_dist = 99999
        for f in food_orbs:
            if f.eaten: continue
            dx = f.x - self.head_x
            dy = f.y - self.head_y
            dist = math.hypot(dx, dy)
            if dist < closest_food_dist:
                closest_food = f
                closest_food_dist = dist
                
        if closest_food and closest_food_dist < 400:
            self.wander_target = QPointF(closest_food.x, closest_food.y)
            if closest_food_dist < 15:
                closest_food.eaten = True
                self.age = max(0, self.age - 200)
                self.food_eaten += 1
                for _ in range(40):
                    p_vx = random.uniform(-3, 3)
                    p_vy = random.uniform(-3, 3)
                    p_color = QColor(255, 255, 150)
                    self.particles_to_emit.append(Particle(closest_food.x, closest_food.y, p_vx, p_vy, p_color, 0.02, s['particle_gravity']))
                
                if s['lifecycle'] and self.food_eaten >= 3:
                    self.food_eaten = 0
                    mutated_hue = (self.base_hue + random.uniform(-0.05, 0.05)) % 1.0
                    dna = {'hue': mutated_hue, 'generation': self.generation}
                    baby = ProceduralCreature(self.head_x, self.head_y, s['creature_segments'], s['seg_length'], dna)
                    baby.age = 0
                    baby.size_mult = 0.1
                    return baby
                    
        elif s['wander_mode']:
            cohesion_x, cohesion_y = 0, 0
            align_x, align_y = 0, 0
            separation_x, separation_y = 0, 0
            neighbor_count = 0
            
            for other in all_creatures:
                if other == self or not other.alive: continue
                dx = other.head_x - self.head_x
                dy = other.head_y - self.head_y
                dist = math.hypot(dx, dy)
                
                if dist < 150:
                    neighbor_count += 1
                    cohesion_x += other.head_x
                    cohesion_y += other.head_y
                    align_x += (other.head_x - other.old_points[0].x())
                    align_y += (other.head_y - other.old_points[0].y())
                    if dist < 50 and dist > 0:
                        separation_x -= dx / dist
                        separation_y -= dy / dist
                        
            if neighbor_count > 0:
                cohesion_x = (cohesion_x / neighbor_count - self.head_x) * s['cohesion']
                cohesion_y = (cohesion_y / neighbor_count - self.head_y) * s['cohesion']
                align_x = (align_x / neighbor_count) * s['alignment']
                align_y = (align_y / neighbor_count) * s['alignment']
                
                self.wander_target.setX(self.head_x + cohesion_x + align_x + separation_x * 5)
                self.wander_target.setY(self.head_y + cohesion_y + align_y + separation_y * 5)
            else:
                self.wander_target.setX(self.head_x + math.cos(self.wander_angle) * 50)
                self.wander_target.setY(self.head_y + math.sin(self.wander_angle) * 50)
                
            closest_prey = None
            closest_pred = None
            closest_prey_dist = 99999
            closest_pred_dist = 99999
            
            for other in all_creatures:
                if other == self or not other.alive: continue
                dx = other.head_x - self.head_x
                dy = other.head_y - self.head_y
                dist = math.hypot(dx, dy)
                
                if self.is_predator and not other.is_predator and dist < closest_prey_dist:
                    closest_prey = other
                    closest_prey_dist = dist
                elif not self.is_predator and other.is_predator and dist < closest_pred_dist:
                    closest_pred = other
                    closest_pred_dist = dist
                    
            if self.is_predator and closest_prey and closest_prey_dist < 300:
                self.wander_target = QPointF(closest_prey.head_x, closest_prey.head_y)
            elif not self.is_predator and closest_pred and closest_pred_dist < 200:
                dx = self.head_x - closest_pred.head_x
                dy = self.head_y - closest_pred.head_y
                self.wander_target = QPointF(self.head_x + dx * 2, self.head_y + dy * 2)
                
            target_x = self.wander_target.x()
            target_y = self.wander_target.y()
        else:
            target_x = s['mouse_pos'].x()
            target_y = s['mouse_pos'].y()

        self.head_x += (target_x - self.head_x) * s['target_smoothing']
        self.head_y += (target_y - self.head_y) * s['target_smoothing']

        net_gravity = s['gravity'] - s['buoyancy']
        for i in range(1, self.segments):
            p = self.points[i]
            old_p = self.old_points[i]
            
            vx = (p.x() - old_p.x()) * s['friction']
            vy = (p.y() - old_p.y()) * s['friction']
            
            self.old_points[i].setX(p.x())
            self.old_points[i].setY(p.y())
            
            if s['body_curl'] > 0:
                t = i / self.segments
                curl_wave = math.sin(t * math.pi * 2 + self.time_offset) * s['body_curl']
                vx += -vy * curl_wave * 0.1
                vy += vx * curl_wave * 0.1
            
            p.setX(p.x() + vx + s['wind_x'])
            p.setY(p.y() + vy + net_gravity + s['wind_y'])

            if s['flow_field'] > 0:
                fx = math.sin(p.x() * 0.005 + flow_time) + math.cos(p.y() * 0.005 + flow_time * 0.7)
                fy = math.cos(p.y() * 0.005 - flow_time) + math.sin(p.x() * 0.005 - flow_time * 0.5)
                p.setX(p.x() + fx * s['flow_field'])
                p.setY(p.y() + fy * s['flow_field'])

            if s['swim_force'] > 0 and i > self.segments * 0.6:
                t = i / self.segments
                swim_wave = math.sin(self.swim_phase - t * 5) * s['swim_force']
                p.setX(p.x() + swim_wave)

            # Ink Defense Mechanism
            if s['mouse_force'] == -1 and s['ink_defense']:
                dx = p.x() - s['mouse_pos'].x()
                dy = p.y() - s['mouse_pos'].y()
                dist = math.hypot(dx, dy)
                if dist < 150 and self.ink_cooldown <= 0:
                    self.ink_cooldown = 100
                    # Flee boost
                    vx += (dx/dist) * 5.0
                    vy += (dy/dist) * 5.0
                    # Emit Ink
                    for _ in range(20):
                        p_vx = random.uniform(-2, 2) - (dx/dist)*2
                        p_vy = random.uniform(-2, 2) - (dy/dist)*2
                        p_color = QColor(20, 20, 30, 200)
                        self.particles_to_emit.append(Particle(p.x(), p.y(), p_vx, p_vy, p_color, 0.02, 0, "ink"))

            if s['mouse_force'] == 2:
                dx = p.x() - s['mouse_pos'].x()
                dy = p.y() - s['mouse_pos'].y()
                dist_sq = dx*dx + dy*dy
                if dist_sq < 40000:
                    dist = math.sqrt(dist_sq) + 0.001
                    tx = -dy / dist
                    ty = dx / dist
                    force = (1 - dist / 200) * 2.0
                    p.setX(p.x() + tx * force * 4.0)
                    p.setY(p.y() + ty * force * 4.0)
                    p.setX(p.x() - (dx / dist) * force * 0.3)
                    p.setY(p.y() - (dy / dist) * force * 0.3)
            elif s['mouse_force'] != 0:
                dx = p.x() - s['mouse_pos'].x()
                dy = p.y() - s['mouse_pos'].y()
                dist_sq = dx*dx + dy*dy
                if dist_sq < 30000:
                    dist = math.sqrt(dist_sq) + 0.001
                    force = (1 - dist / 173) * s['mouse_force'] * 2.0
                    p.setX(p.x() + (dx / dist) * force)
                    p.setY(p.y() + (dy / dist) * force)

            if s['repulsion'] > 0:
                for other in all_creatures:
                    if other == self or not other.alive: continue
                    for j in range(0, other.segments, 3):
                        op = other.points[j]
                        dx = p.x() - op.x()
                        dy = p.y() - op.y()
                        dist_sq = dx*dx + dy*dy
                        if dist_sq < 2500 and dist_sq > 0:
                            dist = math.sqrt(dist_sq)
                            force = (1 - dist / 50) * s['repulsion']
                            p.setX(p.x() + (dx / dist) * force)
                            p.setY(p.y() + (dy / dist) * force)

        self.points[0].setX(self.head_x)
        self.points[0].setY(self.head_y)

        for _ in range(s['stiffness']):
            for i in range(self.segments - 1):
                p1 = self.points[i]
                p2 = self.points[i + 1]
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()
                distance = math.hypot(dx, dy)
                if distance == 0: distance = 0.0001
                difference = (self.segment_length - distance) / distance
                offset_x = dx * difference * 0.5
                offset_y = dy * difference * 0.5
                if i != 0:
                    p1.setX(p1.x() - offset_x)
                    p1.setY(p1.y() - offset_y)
                p2.setX(p2.x() + offset_x)
                p2.setY(p2.y() + offset_y)

        if s['spine_rigidity'] > 0:
            for i in range(1, self.segments - 1):
                p0 = self.points[i-1]
                p1 = self.points[i]
                p2 = self.points[i+1]
                mid_x = (p0.x() + p2.x()) / 2
                mid_y = (p0.y() + p2.y()) / 2
                p1.setX(p1.x() + (mid_x - p1.x()) * s['spine_rigidity'])
                p1.setY(p1.y() + (mid_y - p1.y()) * s['spine_rigidity'])

        for i in range(self.segments):
            p = self.points[i]
            op = self.old_points[i]
            if s['screen_wrap']:
                if p.x() < 0: p.setX(bounds_w); op.setX(bounds_w)
                if p.x() > bounds_w: p.setX(0); op.setX(0)
                if p.y() < 0: p.setY(bounds_h); op.setY(bounds_h)
                if p.y() > bounds_h: p.setY(0); op.setY(0)
            else:
                if p.x() < 0: p.setX(0)
                if p.x() > bounds_w: p.setX(bounds_w)
                if p.y() < 0: p.setY(0)
                if p.y() > bounds_h: p.setY(bounds_h)

        flow_x = math.sin(self.head_x * 0.005 + flow_time) * s['flow_field'] if s['flow_field'] > 0 else 0
        flow_y = math.cos(self.head_y * 0.005 - flow_time) * s['flow_field'] if s['flow_field'] > 0 else 0

        for app in self.appendages:
            anchor = self.points[app.anchor_idx]
            anchor_old = self.old_points[app.anchor_idx]
            vel = QPointF(anchor.x() - anchor_old.x(), anchor.y() - anchor_old.y())
            app.update(anchor, vel, bounds_w, bounds_h, net_gravity, s['friction'], s['wind_x'], s['wind_y'], s['mouse_pos'], s['mouse_force'], s['stiffness'], flow_x, flow_y)
            
        return None

    def get_thickness(self, t, settings):
        s = settings
        wobble = math.sin(t * math.pi * s['wobble_freq'] + self.time_offset * s['global_speed']) * s['wobble_amp']
        
        if s['body_type'] == 0: base_t = (1.0 - t)
        elif s['body_type'] == 1: base_t = math.sin(t * math.pi)
        elif s['body_type'] == 2: base_t = math.sin(t * math.pi * 0.5) if t < 0.5 else math.sin((1.0 - t) * math.pi * 0.5)
        elif s['body_type'] == 3: base_t = 1.0 - t * 0.2
        else: base_t = (1.0 - t)
            
        if t < 0.1:
            head_boost = (0.1 - t) * 10
            base_t += head_boost * s['head_size']
            
        if t > 0.85:
            tail_t = (t - 0.85) / 0.15
            if s['tail_type'] == 1: base_t += math.sin(tail_t * math.pi) * 0.5
            elif s['tail_type'] == 2: base_t = max(base_t, 0.3)
            elif s['tail_type'] == 3: base_t += math.sin(tail_t * math.pi) * 0.8
                
        return max(1.0, (16.0 * base_t + wobble) * self.size_mult)

    def draw(self, painter, settings):
        if not self.alive: return
        
        points = self.points
        n = len(points)
        if n < 2: return

        s = settings
        
        h1 = (self.base_hue + s['hue_shift']) % 1.0
        h2 = (self.base_hue + s['hue_shift'] + s['grad_spread']) % 1.0
        if s['chameleon']:
            depth_t = self.head_y / s['bounds_h']
            h1 = (h1 + depth_t * 0.5) % 1.0
            h2 = (h2 + depth_t * 0.5) % 1.0

        pulse = 1.0
        if s['pulse_amp'] > 0:
            pulse = 1.0 + math.sin(self.time_offset * s['global_speed'] * s['pulse_speed']) * s['pulse_amp']

        left_edge = []
        right_edge = []
        normals = []

        for i in range(n):
            p = points[i]
            p_next = points[i+1] if i < n - 1 else points[i-1]
            dx = p_next.x() - p.x()
            dy = p_next.y() - p.y()
            length = math.hypot(dx, dy)
            if length == 0: length = 0.0001
            nx = -dy / length
            ny = dx / length
            normals.append((nx, ny))
            
            t = i / (n - 1)
            thickness = self.get_thickness(t, s)
            left_edge.append(QPointF(p.x() + nx * thickness, p.y() + ny * thickness))
            right_edge.append(QPointF(p.x() - nx * thickness, p.y() - ny * thickness))

        c1, c2 = self.get_palette_colors(0, s)
        c1_tail, c2_tail = self.get_palette_colors(1, s)
        color_glow = QColor(c1.red(), c1.green(), c1.blue(), int(60 * pulse))

        if s['shadows']:
            max_y = max(p.y() for p in points)
            shadow_x = (left_edge[0].x() + right_edge[0].x()) / 2
            painter.setBrush(QColor(0, 0, 0, 80))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(shadow_x, max_y + 15), 30 * self.size_mult, 8 * self.size_mult)

        if s['webbed_appendages'] and len(self.appendages) > 1:
            painter.setBrush(QColor(c1.red(), c1.green(), c1.blue(), 60))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            for i in range(len(self.appendages)-1):
                app1 = self.appendages[i]
                app2 = self.appendages[i+1]
                if len(app1.points) > 1 and len(app2.points) > 1:
                    p1_tip = app1.points[-1]
                    p2_tip = app2.points[-1]
                    p1_anchor = self.points[app1.anchor_idx]
                    p2_anchor = self.points[app2.anchor_idx]
                    path.moveTo(p1_anchor)
                    path.quadTo(p1_tip, QPointF((p1_tip.x()+p2_tip.x())/2, (p1_tip.y()+p2_tip.y())/2))
                    path.quadTo(p2_tip, p2_anchor)
            painter.drawPath(path)

        for app in self.appendages:
            app.draw(painter, c2, s['wireframe'], self.time_offset, s['global_speed'])

        # Wireframe Mode
        if s['wireframe']:
            painter.setPen(QPen(QColor(255, 255, 255, 150), 1))
            painter.setBrush(Qt.NoBrush)
            for i in range(n):
                p = points[i]
                painter.drawEllipse(p, 2, 2)
                if i < n - 1:
                    painter.drawLine(p, points[i+1])
                    painter.drawLine(left_edge[i], right_edge[i])
            return

        # Skeleton Mode
        if s['skeleton']:
            bone_color = QColor(240, 240, 220, 200)
            painter.setPen(QPen(bone_color, 3))
            painter.setBrush(Qt.NoBrush)
            
            # Spine
            spine_path = QPainterPath()
            spine_path.moveTo(points[0])
            for i in range(n-1):
                p1 = points[i]
                p2 = points[i+1]
                mid = QPointF((p1.x() + p2.x())/2, (p1.y() + p2.y())/2)
                spine_path.quadTo(p1, mid)
            spine_path.lineTo(points[-1])
            painter.drawPath(spine_path)
            
            # Ribs
            painter.setPen(QPen(bone_color, 2))
            for i in range(2, n - 2, 2):
                painter.drawLine(points[i], left_edge[i])
                painter.drawLine(points[i], right_edge[i])
                
            # Skull
            painter.setBrush(bone_color)
            painter.drawEllipse(points[0], self.get_thickness(0, s), self.get_thickness(0, s))
            return

        # Exoskeleton Mode
        if s['exoskeleton']:
            painter.setBrush(QColor(c2.red(), c2.green(), c2.blue(), 200))
            painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
            for i in range(n - 1):
                poly = QPolygonF([left_edge[i], right_edge[i], right_edge[i+1], left_edge[i+1]])
                painter.drawPolygon(poly)
        else:
            path = QPainterPath()
            path.moveTo(left_edge[0])
            for i in range(len(left_edge)-1):
                p1 = left_edge[i]
                p2 = left_edge[i+1]
                mid = QPointF((p1.x() + p2.x())/2, (p1.y() + p2.y())/2)
                path.quadTo(p1, mid)
            path.lineTo(left_edge[-1])
            
            for i in range(len(right_edge)-1, 0, -1):
                p1 = right_edge[i]
                p2 = right_edge[i-1]
                mid = QPointF((p1.x() + p2.x())/2, (p1.y() + p2.y())/2)
                path.quadTo(p1, mid)
            path.lineTo(right_edge[0])
            path.closeSubpath()

            if self.is_predator:
                aura_pen = QPen(QColor(255, 0, 0, 100))
                aura_pen.setWidth(int(s['glow_intensity'] * pulse + 6))
                painter.setPen(aura_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)

            if s['glow_intensity'] > 0:
                glow_pen = QPen(color_glow)
                glow_pen.setWidth(int(s['glow_intensity'] * pulse))
                painter.setPen(glow_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)

            gradient = QLinearGradient(points[0], points[-1])
            gradient.setColorAt(0.0, c1)
            gradient.setColorAt(1.0, c2_tail)
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawPath(path)

        left_tips = []
        right_tips = []
        if s['spike_size'] > 0:
            for i in range(2, n - 2, 3):
                p = points[i]
                nx, ny = normals[i]
                t = i / (n - 1)
                spike_len = self.get_thickness(t, s) * s['spike_size']
                left_tips.append(QPointF(p.x() + nx * spike_len, p.y() + ny * spike_len))
                right_tips.append(QPointF(p.x() - nx * spike_len, p.y() - ny * spike_len))
                
            if s['dorsal_sail']:
                sail_poly = QPolygonF()
                for i in range(len(left_tips)):
                    sail_poly.append(left_tips[i])
                for i in range(len(right_tips)-1, -1, -1):
                    sail_poly.append(right_tips[i])
                if not sail_poly.isEmpty():
                    painter.setBrush(QColor(c2.red(), c2.green(), c2.blue(), 150))
                    painter.setPen(Qt.NoPen)
                    painter.drawPolygon(sail_poly)
            else:
                painter.setBrush(QColor(c2.red(), c2.green(), c2.blue(), 200))
                painter.setPen(Qt.NoPen)
                for tip in left_tips:
                    p = points[2]
                    painter.drawPolygon(QPolygonF([p, tip, QPointF(p.x(), p.y())]))
                for tip in right_tips:
                    p = points[2]
                    painter.drawPolygon(QPolygonF([p, tip, QPointF(p.x(), p.y())]))

        if s['draw_fins']:
            painter.setBrush(QColor(c1.red(), c1.green(), c1.blue(), 80))
            painter.setPen(Qt.NoPen)
            for i in range(2, n - 2, 4):
                p = points[i]
                nx, ny = normals[i]
                fin_size = abs(math.sin(i * 0.5 + self.time_offset * s['global_speed'] * 2)) * 15 + 5
                poly = QPolygonF([p, QPointF(p.x() + nx * fin_size, p.y() + ny * fin_size), QPointF(p.x() + nx * fin_size * 0.5, p.y() + ny * fin_size * 0.5)])
                painter.drawPolygon(poly)
                poly = QPolygonF([p, QPointF(p.x() - nx * fin_size, p.y() - ny * fin_size), QPointF(p.x() - nx * fin_size * 0.5, p.y() - ny * fin_size * 0.5)])
                painter.drawPolygon(poly)

        if s['pattern_type'] == 1:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 120))
            for i in range(2, n - 2, 3):
                p = points[i]
                nx, ny = normals[i]
                t = i / (n - 1)
                th = self.get_thickness(t, s)
                poly = QPolygonF([
                    QPointF(p.x() + nx * th, p.y() + ny * th),
                    QPointF(p.x() - nx * th, p.y() - ny * th),
                    QPointF(points[i+1].x() - nx * th, points[i+1].y() - ny * th),
                    QPointF(points[i+1].x() + nx * th, points[i+1].y() + ny * th)
                ])
                painter.drawPolygon(poly)
        elif s['pattern_type'] == 2:
            painter.setBrush(QColor(0, 0, 0, 150))
            for i in range(3, n - 2, 4):
                p = points[i]
                t = i / (n - 1)
                th = self.get_thickness(t, s)
                painter.drawEllipse(p, th * 0.5, th * 0.5)
        elif s['pattern_type'] == 3:
            painter.setPen(QPen(QColor(0, 0, 0, 180), 2))
            for i in range(2, n - 2, 2):
                painter.drawLine(left_edge[i], right_edge[i])
        elif s['pattern_type'] == 4:
            painter.setPen(QPen(QColor(0, 0, 0, 100), 1))
            painter.setBrush(Qt.NoBrush)
            for i in range(1, n - 1, 2):
                p = points[i]
                nx, ny = normals[i]
                t = i / (n - 1)
                th = self.get_thickness(t, s)
                rect_l = QRectF(p.x() - th, p.y() - th, th * 2, th * 2)
                angle = math.degrees(math.atan2(ny, nx))
                painter.drawArc(rect_l, int(angle * 16 - 45 * 16), 90 * 16)
                rect_r = QRectF(p.x() - th, p.y() - th, th * 2, th * 2)
                painter.drawArc(rect_r, int(angle * 16 + 135 * 16), 90 * 16)

        if s['vein_thickness'] > 0 or s['vein_type'] == 1:
            vein_color = QColor.fromHslF(h1, s['color_sat'] * 0.5, 1.0) if s['palette'] == 0 else c1.lighter(150)
            
            if s['vein_type'] == 1:
                vein_pen = QPen(vein_color, s['vein_thickness'] if s['vein_thickness'] > 0 else 2)
                painter.setPen(vein_pen)
                for i in range(len(points)-2):
                    p1 = points[i]
                    p2 = points[i+1]
                    offset_x = random.uniform(-4, 4)
                    offset_y = random.uniform(-4, 4)
                    mid = QPointF((p1.x()+p2.x())/2 + offset_x, (p1.y()+p2.y())/2 + offset_y)
                    painter.drawLine(p1, mid)
                    painter.drawLine(mid, p2)
            else:
                vein_path = QPainterPath()
                vein_path.moveTo(points[0])
                for i in range(len(points)-1):
                    p1 = points[i]
                    p2 = points[i+1]
                    mid = QPointF((p1.x() + p2.x())/2, (p1.y() + p2.y())/2)
                    vein_path.quadTo(p1, mid)
                vein_path.lineTo(points[-1])
                vein_pen = QPen(vein_color)
                vein_pen.setWidthF(s['vein_thickness'])
                vein_pen.setCapStyle(Qt.RoundCap)
                painter.setPen(vein_pen)
                painter.drawPath(vein_path)

        head = points[0]
        neck = points[1]
        dx = head.x() - neck.x()
        dy = head.y() - neck.y()
        length = math.hypot(dx, dy) + 0.001
        fx, fy = dx / length, dy / length 
        px, py = -fy, fx 
        
        if s['gill_size'] > 0:
            gill_open = (math.sin(self.time_offset * s['global_speed'] * 4) + 1) * 0.5
            gill_len = 4 + s['gill_size'] * 2
            gill_wid = 2 + s['gill_size'] + (gill_open * 3)
            painter.setPen(QPen(c2.darker(150), 1.5))
            painter.setBrush(QColor(100, 0, 0, 150))
            poly_l = QPolygonF([
                QPointF(neck.x() + px * 3, neck.y() + py * 3),
                QPointF(neck.x() + fx * gill_len + px * gill_wid, neck.y() + fy * gill_len + py * gill_wid),
                QPointF(neck.x() + fx * gill_len + px * 2, neck.y() + fy * gill_len + py * 2)
            ])
            painter.drawPolygon(poly_l)
            poly_r = QPolygonF([
                QPointF(neck.x() - px * 3, neck.y() - py * 3),
                QPointF(neck.x() + fx * gill_len - px * gill_wid, neck.y() + fy * gill_len - py * gill_wid),
                QPointF(neck.x() + fx * gill_len - px * 2, neck.y() + fy * gill_len - py * 2)
            ])
            painter.drawPolygon(poly_r)
            
            if random.random() < 0.05 * s['global_speed']:
                bx = neck.x() - px * gill_wid
                by = neck.y() - py * gill_wid
                self.particles_to_emit.append(Particle(bx, by, random.uniform(-0.5, 0.5), random.uniform(-1, -2), QColor(200, 255, 255, 100), 0.01, 0, "bubble"))

        if s['mouth_size'] > 0:
            mouth_open = (math.sin(self.time_offset * s['global_speed'] * 3) + 1) * 0.5 * s['mouth_size']
            jaw_len = 6 + s['mouth_size'] * 2
            jaw_wid = 3 + s['mouth_size']
            painter.setBrush(QColor(20, 0, 0))
            painter.setPen(QPen(c2, 1.5))
            poly_top = QPolygonF([head, QPointF(head.x() + fx * jaw_len, head.y() + fy * jaw_len), QPointF(head.x() + fx * (jaw_len/2) + px * jaw_wid, head.y() + fy * (jaw_len/2) + py * jaw_wid)])
            painter.drawPolygon(poly_top)
            poly_bot = QPolygonF([head, QPointF(head.x() + fx * (jaw_len + mouth_open), head.y() + fy * (jaw_len + mouth_open)), QPointF(head.x() + fx * (jaw_len/2) - px * (jaw_wid + mouth_open), head.y() + fy * (jaw_len/2) - py * (jaw_wid + mouth_open))])
            painter.drawPolygon(poly_bot)

        num_eyes = s['eye_count']
        eye_size = s['eye_size']
        for i in range(num_eyes):
            if num_eyes == 1:
                offset_p = 0.0
                offset_f = 0.3
            else:
                t = i / (num_eyes - 1)
                offset_p = (t - 0.5) * 2.0 
                offset_f = 0.2 + abs(t - 0.5) * 0.5
            
            ex = head.x() + fx * offset_f * 5 + px * offset_p * 4
            ey = head.y() + fy * offset_f * 5 + py * offset_p * 4
            
            if s['eye_type'] == 2:
                painter.setBrush(QColor(255, 255, 255, 200))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(ex, ey), eye_size * 1.2, eye_size * 1.2)
                continue
                
            iris_color = QColor.fromHslF((h1 + 0.5) % 1.0, 1.0, 0.5) if s['palette'] == 0 else c1.lighter(150)
            painter.setBrush(iris_color)
            painter.drawEllipse(QPointF(ex, ey), eye_size, eye_size)
            
            dx_m = s['mouse_pos'].x() - ex
            dy_m = s['mouse_pos'].y() - ey
            dist_m = math.hypot(dx_m, dy_m)
            pupil_dilation = 1.0 - min(1.0, dist_m / 200.0)
            
            pupil_x = ex + (dx_m / (dist_m+0.001)) * eye_size * 0.3
            pupil_y = ey + (dy_m / (dist_m+0.001)) * eye_size * 0.3
            
            pupil_size = eye_size * (0.5 - pupil_dilation * 0.3)
            
            painter.setBrush(QColor(0, 0, 0))
            if s['eye_type'] == 1:
                painter.drawEllipse(QPointF(pupil_x, pupil_y), pupil_size * 0.4, pupil_size * 1.5)
            else:
                painter.drawEllipse(QPointF(pupil_x, pupil_y), pupil_size, pupil_size)


class AnimationWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setMinimumSize(600, 400)
        
        self.settings = {
            "gravity": 0.3, "buoyancy": 0.0, "seg_length": 12, "friction": 0.98,
            "wind_x": 0.0, "wind_y": 0.0, "wander_mode": False, "mouse_pos": QPointF(400, 300),
            "mouse_force": 0, "hue_shift": 0.0, "draw_fins": True, "body_type": 0,
            "tail_type": 0, "pattern_type": 0, "app_type": 0,
            "wobble_amp": 1.5, "wobble_freq": 6.0, "target_smoothing": 0.1,
            "stiffness": 5, "particle_emission": 0.4, "particle_lifespan": 0.015,
            "trail_fade": 40, "creature_segments": 20, "has_appendages": True,
            "app_count": 3, "app_length": 8, "webbed_appendages": False,
            "has_head_app": False, "head_app_count": 2, "lure_light": False,
            "swim_force": 0.0, "swim_freq": 1.0, "global_speed": 1.0,
            "head_size": 1.0, "eye_count": 2, "eye_size": 3.5, "eye_type": 0, "spike_size": 0.0,
            "glow_intensity": 4, "color_sat": 0.85, "color_light": 0.6, "grad_spread": 0.15,
            "vein_thickness": 0.0, "vein_type": 0, "mouth_size": 0.0, "gill_size": 0.0,
            "wireframe": False, "skeleton": False, "exoskeleton": False, "particle_gravity": -0.05, "shadows": False,
            "repulsion": 0.0, "lifecycle": False, "target_count": 5,
            "cohesion": 0.0, "alignment": 0.0, "screen_wrap": False, "body_curl": 0.0,
            "spine_rigidity": 0.0, "pulse_speed": 0.1, "pulse_amp": 0.0, "chameleon": False,
            "palette": 0, "bounds_w": 800, "bounds_h": 600, "additive_particles": True,
            "flow_field": 0.0, "kelp_forest": False, "dorsal_sail": False,
            "pulse_size": 0.0, "ink_defense": False
        }
        
        self.creatures = []
        self.particles = []
        self.food_orbs = []
        self.kelp_strands = []
        self.flow_time = 0.0
        
        for _ in range(5):
            self.add_creature()
            
        self.trail_canvas = QPixmap(self.size())
        self.trail_canvas.fill(QColor(15, 15, 25))
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)
        
    def resizeEvent(self, event):
        new_canvas = QPixmap(event.size())
        new_canvas.fill(QColor(15, 15, 25))
        painter = QPainter(new_canvas)
        painter.drawPixmap(0, 0, self.trail_canvas)
        painter.end()
        self.trail_canvas = new_canvas
        self.settings['bounds_w'] = self.width()
        self.settings['bounds_h'] = self.height()
        if self.settings['kelp_forest']:
            self.generate_kelp()
        super().resizeEvent(event)
        
    def add_creature(self):
        x = random.randint(100, max(101, self.width()-100))
        y = random.randint(100, max(101, self.height()-100))
        c = ProceduralCreature(x, y, segments=self.settings['creature_segments'], segment_length=self.settings['seg_length'])
        
        if self.settings['has_appendages']:
            count = self.settings['app_count']
            for _ in range(count):
                idx = random.randint(2, c.segments - 3)
                app_len = self.settings['app_length']
                app = Appendage(idx, app_len, self.settings['seg_length'] * 0.8, self.settings['app_type'])
                app.init_points(c.points[idx])
                c.appendages.append(app)
                
        if self.settings['has_head_app']:
            for _ in range(self.settings['head_app_count']):
                idx = random.randint(0, 1)
                app_len = self.settings['app_length']
                app = Appendage(idx, app_len, self.settings['seg_length'] * 1.2, 0, self.settings['lure_light'])
                app.init_points(c.points[idx])
                c.appendages.append(app)
                
        self.creatures.append(c)
        
    def generate_kelp(self):
        self.kelp_strands.clear()
        if not self.settings['kelp_forest']: return
        for _ in range(15):
            x = random.randint(0, self.width())
            segs = random.randint(10, 25)
            length = random.randint(10, 20)
            self.kelp_strands.append(KelpStrand(x, self.height(), segs, length))
        
    def drop_food(self):
        x = random.randint(50, max(51, self.width()-50))
        y = random.randint(50, max(51, self.height()-50))
        self.food_orbs.append(FoodOrb(x, y))
        
    def clear_creatures(self):
        self.creatures.clear()
        self.particles.clear()
        self.food_orbs.clear()
        
    def toggle_wander(self, state):
        self.settings['wander_mode'] = state
        if state:
            for c in self.creatures:
                c.wander_target = QPointF(c.points[0])
                c.wander_angle = random.uniform(0, math.pi*2)
                
    def mouseMoveEvent(self, event):
        self.settings['mouse_pos'] = event.position()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.settings['mouse_force'] = 1
        elif event.button() == Qt.RightButton:
            self.settings['mouse_force'] = -1
        elif event.button() == Qt.MiddleButton:
            self.settings['mouse_force'] = 2
            
    def mouseReleaseEvent(self, event):
        self.settings['mouse_force'] = 0
        
    def update_animation(self):
        s = self.settings
        self.flow_time += 0.005 * s['global_speed']
        
        if s['kelp_forest']:
            flow_y = math.cos(0 - self.flow_time) * s['flow_field'] if s['flow_field'] > 0 else 0
            for k in self.kelp_strands:
                k.update(s['wind_x'], flow_y, self.height())
        
        for f in self.food_orbs[:]:
            f.update(s['global_speed'])
            if f.eaten:
                self.food_orbs.remove(f)
                
        if s['lifecycle']:
            alive_creatures = []
            newborns = []
            for c in self.creatures:
                if c.alive:
                    alive_creatures.append(c)
                else:
                    for _ in range(30):
                        p_vx = random.uniform(-3, 3)
                        p_vy = random.uniform(-3, 3)
                        h1 = (c.base_hue + s['hue_shift']) % 1.0
                        p_color = QColor.fromHslF(h1, s['color_sat'], s['color_light'])
                        self.particles.append(Particle(c.points[0].x(), c.points[0].y(), p_vx, p_vy, p_color, 0.02, s['particle_gravity']))
            self.creatures = alive_creatures
            
            for c in self.creatures:
                baby = c.update(0, 0, self.width(), self.height(), s, self.creatures + newborns, self.food_orbs, self.flow_time)
                if baby:
                    newborns.append(baby)
            self.creatures.extend(newborns)
            
            while len(self.creatures) < s['target_count']:
                self.add_creature()
                self.creatures[-1].age = 0 
                self.creatures[-1].size_mult = 0.1
        else:
            for c in self.creatures:
                c.update(0, 0, self.width(), self.height(), s, self.creatures, self.food_orbs, self.flow_time)
            
        for c in self.creatures:
            if hasattr(c, 'particles_to_emit'):
                for p in c.particles_to_emit:
                    self.particles.append(p)
                c.particles_to_emit.clear()
            
            tail = c.points[-1]
            tail_old = c.old_points[-1]
            speed = math.hypot(tail.x() - tail_old.x(), tail.y() - tail_old.y())
            if speed > 1.0 and random.random() < s['particle_emission']:
                h1 = (c.base_hue + s['hue_shift']) % 1.0
                p_color = QColor.fromHslF(h1, s['color_sat'], s['color_light'])
                if s['palette'] != 0:
                    c1, _ = c.get_palette_colors(0, s)
                    p_color = c1
                p_vx = random.uniform(-1, 1)
                p_vy = random.uniform(-1, 1)
                self.particles.append(Particle(tail.x(), tail.y(), p_vx, p_vy, p_color, s['particle_lifespan'], s['particle_gravity']))
        
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)
                
        self.update()
        
    def paintEvent(self, event):
        s = self.settings
        canvas_painter = QPainter(self.trail_canvas)
        canvas_painter.fillRect(self.trail_canvas.rect(), QColor(15, 15, 25, s['trail_fade'])) 
        
        if s['kelp_forest']:
            for k in self.kelp_strands:
                k.draw(canvas_painter)
                
        for f in self.food_orbs:
            f.draw(canvas_painter)
            
        if s['additive_particles']:
            canvas_painter.setCompositionMode(QPainter.CompositionMode_Plus)
        for p in self.particles:
            p.draw(canvas_painter)
        if s['additive_particles']:
            canvas_painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
        for c in self.creatures:
            c.draw(canvas_painter, s)
        canvas_painter.end()
        
        screen_painter = QPainter(self)
        bg_gradient = QLinearGradient(0, 0, 0, self.height())
        bg_gradient.setColorAt(0, QColor(25, 25, 40))
        bg_gradient.setColorAt(1, QColor(10, 10, 15))
        screen_painter.fillRect(self.rect(), bg_gradient)
        
        screen_painter.drawPixmap(0, 0, self.trail_canvas)
        
        if s['mouse_force'] != 0:
            screen_painter.setPen(Qt.NoPen)
            if s['mouse_force'] == 1:
                screen_painter.setBrush(QColor(0, 255, 200, 30))
                screen_painter.drawEllipse(s['mouse_pos'], 173, 173)
            elif s['mouse_force'] == -1:
                screen_painter.setBrush(QColor(255, 50, 50, 30))
                screen_painter.drawEllipse(s['mouse_pos'], 173, 173)
            elif s['mouse_force'] == 2:
                screen_painter.setBrush(QColor(150, 0, 255, 40))
                screen_painter.drawEllipse(s['mouse_pos'], 200, 200)
                pen = QPen(QColor(255, 255, 255, 80), 2)
                screen_painter.setPen(pen)
                screen_painter.setBrush(Qt.NoBrush)
                for i in range(3):
                    angle = self.timer.remainingTime() * 0.1 + i * 120
                    screen_painter.drawArc(QRectF(s['mouse_pos'].x()-150, s['mouse_pos'].y()-150, 300, 300), int(angle*16), int(90*16))


class ControlPanel(QWidget):
    def __init__(self, anim_widget):
        super().__init__()
        self.anim_widget = anim_widget
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)
        
        title = QLabel("Genesis Lab v11.0")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #00ffcc;")
        layout.addWidget(title)
        
        # Biome Presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Biome:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Custom", "Deep Sea", "Magma Vents", "Toxic Swamp", "Ghostly", "Cosmic Void"])
        self.preset_combo.currentIndexChanged.connect(self.apply_preset)
        preset_layout.addWidget(self.preset_combo)
        layout.addLayout(preset_layout)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # --- Tab 1: Environment ---
        env_tab = QWidget()
        env_layout = QVBoxLayout(env_tab)
        self.gravity_slider = self.create_slider(0, 100, 30, "Gravity", env_layout)
        self.buoyancy_slider = self.create_slider(0, 100, 0, "Buoyancy (Anti-Gravity)", env_layout)
        self.friction_slider = self.create_slider(80, 100, 98, "Friction", env_layout)
        self.windx_slider = self.create_slider(-100, 100, 0, "Wind X", env_layout)
        self.windy_slider = self.create_slider(-100, 100, 0, "Wind Y", env_layout)
        self.flow_slider = self.create_slider(0, 100, 0, "Flow Field (Procedural Currents)", env_layout)
        self.smoothing_slider = self.create_slider(1, 50, 10, "Target Smoothing", env_layout)
        self.stiffness_slider = self.create_slider(1, 15, 5, "Stiffness (Iterations)", env_layout)
        self.rigidity_slider = self.create_slider(0, 100, 0, "Spine Rigidity (Anti-Kink)", env_layout)
        self.curl_slider = self.create_slider(0, 50, 0, "Body Curl (Slither)", env_layout)
        self.pulse_size_slider = self.create_slider(0, 50, 0, "Jet Pulse Size", env_layout)
        
        self.wrap_check = QCheckBox("Screen Wrap (Infinite Ocean)")
        self.wrap_check.stateChanged.connect(lambda s: self.update_setting('screen_wrap', bool(s)))
        env_layout.addWidget(self.wrap_check)
        self.ink_check = QCheckBox("Ink Defense Mechanism")
        self.ink_check.stateChanged.connect(lambda s: self.update_setting('ink_defense', bool(s)))
        env_layout.addWidget(self.ink_check)
        self.kelp_check = QCheckBox("Procedural Kelp Forest (Background)")
        self.kelp_check.stateChanged.connect(lambda s: [self.update_setting('kelp_forest', bool(s)), self.anim_widget.generate_kelp()])
        env_layout.addWidget(self.kelp_check)
        self.wander_check = QCheckBox("Autonomous AI / Boids")
        self.wander_check.stateChanged.connect(self.anim_widget.toggle_wander)
        env_layout.addWidget(self.wander_check)
        env_layout.addStretch()
        self.tabs.addTab(env_tab, "Environment")
        
        # --- Tab 2: Boids & AI ---
        boids_tab = QWidget()
        boids_layout = QVBoxLayout(boids_tab)
        self.repulsion_slider = self.create_slider(0, 100, 0, "Separation (Repulsion)", boids_layout)
        self.cohesion_slider = self.create_slider(0, 100, 0, "Cohesion (Grouping)", boids_layout)
        self.alignment_slider = self.create_slider(0, 100, 0, "Alignment (Matching Speed/Dir)", boids_layout)
        boids_layout.addStretch()
        self.tabs.addTab(boids_tab, "Boids & AI")
        
        # --- Tab 3: Morphology ---
        morph_tab = QWidget()
        morph_layout = QVBoxLayout(morph_tab)
        
        morph_layout.addWidget(QLabel("Body Type:"))
        self.body_combo = QComboBox()
        self.body_combo.addItems(["Tapered", "Bulbous", "Spear", "Uniform"])
        self.body_combo.currentIndexChanged.connect(lambda i: self.update_setting('body_type', i))
        morph_layout.addWidget(self.body_combo)
        
        morph_layout.addWidget(QLabel("Tail Type:"))
        self.tail_combo = QComboBox()
        self.tail_combo.addItems(["Pointed", "Fan", "Blunt", "Spade"])
        self.tail_combo.currentIndexChanged.connect(lambda i: self.update_setting('tail_type', i))
        morph_layout.addWidget(self.tail_combo)
        
        morph_layout.addWidget(QLabel("Appendage Type:"))
        self.app_combo = QComboBox()
        self.app_combo.addItems(["Tentacle", "Spike", "Fin"])
        self.app_combo.currentIndexChanged.connect(lambda i: self.update_setting('app_type', i))
        morph_layout.addWidget(self.app_combo)
        
        self.segs_slider = self.create_slider(10, 40, 20, "Segment Count", morph_layout)
        self.seg_slider = self.create_slider(5, 30, 12, "Segment Length", morph_layout)
        self.wobble_amp_slider = self.create_slider(0, 50, 15, "Wobble Amplitude", morph_layout)
        self.wobble_freq_slider = self.create_slider(1, 150, 60, "Wobble Frequency", morph_layout)
        self.swim_force_slider = self.create_slider(0, 50, 0, "Swim Force (Tail Flapping)", morph_layout)
        self.swim_freq_slider = self.create_slider(1, 100, 20, "Swim Frequency", morph_layout)
        
        self.fins_check = QCheckBox("Procedural Fins")
        self.fins_check.setChecked(True)
        self.fins_check.stateChanged.connect(lambda s: self.update_setting('draw_fins', bool(s)))
        morph_layout.addWidget(self.fins_check)
        
        self.app_check = QCheckBox("Enable Body Appendages")
        self.app_check.setChecked(True)
        self.app_check.stateChanged.connect(lambda s: self.update_setting('has_appendages', bool(s)))
        morph_layout.addWidget(self.app_check)
        self.app_count_slider = self.create_slider(1, 6, 3, "Appendage Count", morph_layout)
        self.app_len_slider = self.create_slider(4, 15, 8, "Appendage Length", morph_layout)
        
        self.web_check = QCheckBox("Webbed Appendages (Manta Wings)")
        self.web_check.stateChanged.connect(lambda s: self.update_setting('webbed_appendages', bool(s)))
        morph_layout.addWidget(self.web_check)
        
        self.head_app_check = QCheckBox("Enable Head Lures/Antennae")
        self.head_app_check.stateChanged.connect(lambda s: self.update_setting('has_head_app', bool(s)))
        morph_layout.addWidget(self.head_app_check)
        self.head_app_slider = self.create_slider(1, 4, 2, "Head Appendage Count", morph_layout)
        self.lure_check = QCheckBox("Glowing Lure Tip (Anglerfish)")
        self.lure_check.stateChanged.connect(lambda s: self.update_setting('lure_light', bool(s)))
        morph_layout.addWidget(self.lure_check)
        
        morph_layout.addStretch()
        self.tabs.addTab(morph_tab, "Morphology")
        
        # --- Tab 4: Anatomy ---
        ana_tab = QWidget()
        ana_layout = QVBoxLayout(ana_tab)
        self.head_size_slider = self.create_slider(0, 40, 10, "Head Size Boost", ana_layout)
        self.mouth_slider = self.create_slider(0, 50, 0, "Mouth/Jaw Size", ana_layout)
        self.gill_slider = self.create_slider(0, 30, 0, "Gill Size", ana_layout)
        
        ana_layout.addWidget(QLabel("Eye Type:"))
        self.eye_combo = QComboBox()
        self.eye_combo.addItems(["Round", "Slit (Reptilian)", "Glowing (Entity)"])
        self.eye_combo.currentIndexChanged.connect(lambda i: self.update_setting('eye_type', i))
        ana_layout.addWidget(self.eye_combo)
        self.eye_count_slider = self.create_slider(1, 8, 2, "Eye Count", ana_layout)
        self.eye_size_slider = self.create_slider(10, 80, 35, "Eye Size", ana_layout)
        
        self.spike_slider = self.create_slider(0, 30, 0, "Spike/Scute Size", ana_layout)
        self.sail_check = QCheckBox("Dorsal Sail (Spinosaurus)")
        self.sail_check.stateChanged.connect(lambda s: self.update_setting('dorsal_sail', bool(s)))
        ana_layout.addWidget(self.sail_check)
        
        ana_layout.addWidget(QLabel("Spine Vein Type:"))
        self.vein_combo = QComboBox()
        self.vein_combo.addItems(["Smooth Vein", "Electric Arc"])
        self.vein_combo.currentIndexChanged.connect(lambda i: self.update_setting('vein_type', i))
        ana_layout.addWidget(self.vein_combo)
        self.vein_slider = self.create_slider(0, 80, 0, "Vein Thickness", ana_layout)
        
        ana_layout.addStretch()
        self.tabs.addTab(ana_tab, "Anatomy")
        
        # --- Tab 5: Visuals ---
        vis_tab = QWidget()
        vis_layout = QVBoxLayout(vis_tab)
        
        vis_layout.addWidget(QLabel("Color Palette:"))
        self.pal_combo = QComboBox()
        self.pal_combo.addItems(["Neon Abyss (HSL)", "Magma", "Toxic Swamp", "Spectral Rainbow", "Monochrome"])
        self.pal_combo.currentIndexChanged.connect(lambda i: self.update_setting('palette', i))
        vis_layout.addWidget(self.pal_combo)
        
        self.glow_slider = self.create_slider(0, 15, 4, "Glow Intensity (Width)", vis_layout)
        self.pulse_spd_slider = self.create_slider(0, 100, 10, "Bioluminescent Pulse Speed", vis_layout)
        self.pulse_amp_slider = self.create_slider(0, 100, 0, "Bioluminescent Pulse Amplitude", vis_layout)
        
        self.cam_check = QCheckBox("Depth Camouflage (Chameleon)")
        self.cam_check.stateChanged.connect(lambda s: self.update_setting('chameleon', bool(s)))
        vis_layout.addWidget(self.cam_check)
        
        self.shadow_check = QCheckBox("Depth Shadows (3D Grounding)")
        self.shadow_check.stateChanged.connect(lambda s: self.update_setting('shadows', bool(s)))
        vis_layout.addWidget(self.shadow_check)
        
        self.hue_slider = self.create_slider(0, 100, 0, "Hue Shift", vis_layout)
        self.sat_slider = self.create_slider(0, 100, 85, "Color Saturation", vis_layout)
        self.light_slider = self.create_slider(10, 90, 60, "Color Brightness", vis_layout)
        self.grad_slider = self.create_slider(0, 50, 15, "Gradient Spread", vis_layout)
        self.trail_slider = self.create_slider(10, 100, 40, "Trail Fade Speed", vis_layout)
        
        self.add_check = QCheckBox("Additive Particle Blending (HDR Glow)")
        self.add_check.setChecked(True)
        self.add_check.stateChanged.connect(lambda s: self.update_setting('additive_particles', bool(s)))
        vis_layout.addWidget(self.add_check)
        
        self.emit_slider = self.create_slider(0, 100, 40, "Particle Emission", vis_layout)
        self.life_slider = self.create_slider(1, 50, 15, "Particle Lifespan", vis_layout)
        self.pgrav_slider = self.create_slider(-50, 50, -5, "Particle Gravity", vis_layout)
        self.speed_slider = self.create_slider(10, 300, 100, "Global Speed Multiplier", vis_layout)
        vis_layout.addStretch()
        self.tabs.addTab(vis_tab, "Visuals")

        # --- Tab 6: Patterns ---
        pat_tab = QWidget()
        pat_layout = QVBoxLayout(pat_tab)
        pat_layout.addWidget(QLabel("Skin Pattern:"))
        self.pat_combo = QComboBox()
        self.pat_combo.addItems(["Solid", "Stripes", "Spots", "Segments", "Scales"])
        self.pat_combo.currentIndexChanged.connect(lambda i: self.update_setting('pattern_type', i))
        pat_layout.addWidget(self.pat_combo)
        pat_layout.addStretch()
        self.tabs.addTab(pat_tab, "Patterns")
        
        # --- Tab 7: Lifecycle ---
        life_tab = QWidget()
        life_layout = QVBoxLayout(life_tab)
        self.life_check = QCheckBox("Enable Lifecycle & Genetics")
        self.life_check.stateChanged.connect(lambda s: self.update_setting('lifecycle', bool(s)))
        life_layout.addWidget(self.life_check)
        self.target_slider = self.create_slider(1, 30, 5, "Target Population Count", life_layout)
        
        self.food_btn = QPushButton("Drop Food")
        self.food_btn.clicked.connect(self.anim_widget.drop_food)
        life_layout.addWidget(self.food_btn)
        life_layout.addStretch()
        self.tabs.addTab(life_tab, "Lifecycle")

        # --- Tab 8: Rendering ---
        rend_tab = QWidget()
        rend_layout = QVBoxLayout(rend_tab)
        self.exo_check = QCheckBox("Exoskeleton Mode (Plates)")
        self.exo_check.stateChanged.connect(lambda s: self.update_setting('exoskeleton', bool(s)))
        rend_layout.addWidget(self.exo_check)
        self.skel_check = QCheckBox("Skeleton / X-Ray Mode")
        self.skel_check.stateChanged.connect(lambda s: self.update_setting('skeleton', bool(s)))
        rend_layout.addWidget(self.skel_check)
        self.wire_check = QCheckBox("Wireframe Debug Mode")
        self.wire_check.stateChanged.connect(lambda s: self.update_setting('wireframe', bool(s)))
        rend_layout.addWidget(self.wire_check)
        rend_layout.addStretch()
        self.tabs.addTab(rend_tab, "Rendering")
        
        # --- Bottom Controls ---
        bottom_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.anim_widget.add_creature)
        bottom_layout.addWidget(self.add_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.anim_widget.clear_creatures)
        bottom_layout.addWidget(self.clear_btn)
        layout.addLayout(bottom_layout)
        
        self.count_label = QLabel("Creatures: 0 | Gen: 0 | Food: 0")
        self.count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.count_label)
        
        self.setStyleSheet("""
            QWidget { background-color: #12121a; color: #c0c0c0; }
            QTabWidget::pane { border: 1px solid #2a2a4e; border-radius: 4px; }
            QTabBar::tab { background: #1a1a24; padding: 8px 12px; border: 1px solid #2a2a4e; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #2a2a4e; color: #00ffcc; }
            QPushButton { background-color: #2a2a4e; border: 1px solid #4a4a6e; padding: 8px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #3a3a6e; color: white; }
            QCheckBox, QLabel { color: #e0e0e0; }
            QComboBox { background-color: #2a2a4e; border: 1px solid #4a4a6e; padding: 4px; border-radius: 2px; }
            QSlider::groove:horizontal { border: 1px solid #4a4a6e; height: 4px; background: #2a2a4e; border-radius: 2px; }
            QSlider::handle:horizontal { background: #00ffcc; width: 12px; margin: -5px 0; border-radius: 6px; }
            QSlider::sub-page:horizontal { background: #00ffcc; border-radius: 2px; }
        """)

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.sync_ui)
        self.ui_timer.start(100)

    def apply_preset(self, index):
        # 0: Custom, 1: Deep Sea, 2: Magma, 3: Toxic, 4: Ghostly, 5: Cosmic
        presets = [
            {}, # Custom does nothing
            {"gravity": 50, "buoyancy": 50, "palette": 0, "glow": 8, "pulse_amp": 30, "shadows": True, "kelp": True, "lure": True, "gill": 20, "mouth": 30, "flow": 30, "rigidity": 80, "wander": True, "segs": 25},
            {"gravity": 80, "buoyancy": 0, "palette": 1, "glow": 5, "pulse_amp": 10, "shadows": True, "kelp": False, "lure": False, "gill": 0, "mouth": 20, "flow": 20, "rigidity": 50, "wander": True, "segs": 15, "spike": 10},
            {"gravity": 20, "buoyancy": 20, "palette": 2, "glow": 6, "pulse_amp": 0, "shadows": False, "kelp": True, "lure": False, "gill": 30, "mouth": 0, "flow": 50, "rigidity": 20, "wander": True, "segs": 30, "emit": 80},
            {"gravity": 0, "buoyancy": 0, "palette": 4, "glow": 10, "pulse_amp": 50, "shadows": False, "kelp": False, "lure": False, "gill": 0, "mouth": 0, "flow": 10, "rigidity": 90, "wander": True, "segs": 40, "trail": 15, "eye_type": 2},
            {"gravity": 0, "buoyancy": 0, "palette": 3, "glow": 12, "pulse_amp": 20, "shadows": True, "kelp": False, "lure": False, "gill": 0, "mouth": 0, "flow": 80, "rigidity": 90, "wander": True, "segs": 30, "wrap": True}
        ]
        
        p = presets[index]
        if not p: return
        
        self.gravity_slider.setValue(p.get("gravity", 30))
        self.buoyancy_slider.setValue(p.get("buoyancy", 0))
        self.pal_combo.setCurrentIndex(p.get("palette", 0))
        self.glow_slider.setValue(p.get("glow", 4))
        self.pulse_amp_slider.setValue(p.get("pulse_amp", 0))
        self.shadow_check.setChecked(p.get("shadows", False))
        self.kelp_check.setChecked(p.get("kelp", False))
        self.lure_check.setChecked(p.get("lure", False))
        self.gill_slider.setValue(p.get("gill", 0))
        self.mouth_slider.setValue(p.get("mouth", 0))
        self.flow_slider.setValue(p.get("flow", 0))
        self.rigidity_slider.setValue(p.get("rigidity", 0))
        self.wander_check.setChecked(p.get("wander", False))
        self.segs_slider.setValue(p.get("segs", 20))
        self.spike_slider.setValue(p.get("spike", 0))
        self.emit_slider.setValue(p.get("emit", 40))
        self.trail_slider.setValue(p.get("trail", 40))
        self.eye_combo.setCurrentIndex(p.get("eye_type", 0))
        self.wrap_check.setChecked(p.get("wrap", False))

    def update_setting(self, key, val):
        self.anim_widget.settings[key] = val

    def create_slider(self, min_val, max_val, init_val, name, layout):
        lbl = QLabel(f"{name}: {init_val}")
        layout.addWidget(lbl)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(init_val)
        layout.addWidget(slider)
        slider.valueChanged.connect(lambda v: lbl.setText(f"{name}: {v}"))
        return slider

    def sync_ui(self):
        s = self.anim_widget.settings
        s['gravity'] = self.gravity_slider.value() / 100.0
        s['buoyancy'] = self.buoyancy_slider.value() / 100.0
        s['friction'] = self.friction_slider.value() / 100.0
        s['wind_x'] = self.windx_slider.value() / 50.0
        s['wind_y'] = self.windy_slider.value() / 50.0
        s['flow_field'] = self.flow_slider.value() / 100.0
        s['target_smoothing'] = self.smoothing_slider.value() / 100.0
        s['stiffness'] = self.stiffness_slider.value()
        s['spine_rigidity'] = self.rigidity_slider.value() / 100.0
        s['body_curl'] = self.curl_slider.value() / 100.0
        s['pulse_size'] = self.pulse_size_slider.value() / 100.0
        s['seg_length'] = self.seg_slider.value()
        s['creature_segments'] = self.segs_slider.value()
        s['wobble_amp'] = self.wobble_amp_slider.value() / 10.0
        s['wobble_freq'] = self.wobble_freq_slider.value() / 10.0
        s['swim_force'] = self.swim_force_slider.value() / 10.0
        s['swim_freq'] = self.swim_freq_slider.value() / 10.0
        s['head_size'] = self.head_size_slider.value() / 10.0
        s['mouth_size'] = self.mouth_slider.value() / 10.0
        s['gill_size'] = self.gill_slider.value() / 10.0
        s['eye_count'] = self.eye_count_slider.value()
        s['eye_size'] = self.eye_size_slider.value() / 10.0
        s['spike_size'] = self.spike_slider.value() / 10.0
        s['vein_thickness'] = self.vein_slider.value() / 10.0
        s['glow_intensity'] = self.glow_slider.value()
        s['pulse_speed'] = self.pulse_spd_slider.value() / 10.0
        s['pulse_amp'] = self.pulse_amp_slider.value() / 100.0
        s['hue_shift'] = self.hue_slider.value() / 100.0
        s['color_sat'] = self.sat_slider.value() / 100.0
        s['color_light'] = self.light_slider.value() / 100.0
        s['grad_spread'] = self.grad_slider.value() / 100.0
        s['trail_fade'] = self.trail_slider.value()
        s['particle_emission'] = self.emit_slider.value() / 100.0
        s['particle_lifespan'] = self.life_slider.value() / 1000.0
        s['particle_gravity'] = self.pgrav_slider.value() / 100.0
        s['global_speed'] = self.speed_slider.value() / 100.0
        s['app_count'] = self.app_count_slider.value()
        s['app_length'] = self.app_len_slider.value()
        s['head_app_count'] = self.head_app_slider.value()
        s['repulsion'] = self.repulsion_slider.value() / 50.0
        s['cohesion'] = self.cohesion_slider.value() / 500.0
        s['alignment'] = self.alignment_slider.value() / 20.0
        s['target_count'] = self.target_slider.value()
        
        max_gen = max([c.generation for c in self.anim_widget.creatures], default=0)
        self.count_label.setText(f"Creatures: {len(self.anim_widget.creatures)} | Max Gen: {max_gen} | Food: {len(self.anim_widget.food_orbs)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Procedural Genesis Lab v11.0 - PySide6")
        self.resize(1280, 800)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.anim_widget = AnimationWidget()
        self.control_panel = ControlPanel(self.anim_widget)
        
        layout.addWidget(self.anim_widget)
        layout.addWidget(self.control_panel)
        
        self.setStyleSheet("QMainWindow { background-color: #0a0a0f; }")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())