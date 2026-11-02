"""Translate event histories and apply basic shot acceptance checks."""
from ..models import CollisionEvent


def extract_events(system):
    return tuple(CollisionEvent(float(event.time), str(event.event_type), tuple(event.ids)) for event in system.events if event.event_type.is_collision())


def assess_events(events, target_id, pocket_id, numbers, config, completed):
    first = next((next(agent for agent in event.agents if agent != 'cue') for event in events if event.kind == 'ball_ball' and 'cue' in event.agents), None)
    dropped = {event.agents[0]: event.agents[1] for event in events if event.kind == 'ball_pocket'}
    target_pocketed = dropped.get(target_id) == pocket_id
    cue_pocketed = 'cue' in dropped
    if not completed:
        reason = '仿真达到时间或事件上限，结果不作为推荐'
    elif cue_pocketed:
        reason = '母球落袋'
    elif first != target_id:
        reason = '首碰球不是所选目标球'
    elif not target_pocketed:
        reason = '目标球未进入所选模型袋口'
    else:
        unexpected = [bid for bid in dropped if bid not in ('cue', target_id)]
        illegal = [bid for bid in unexpected if numbers[bid] is None or numbers[bid] == 8 or (config.target_group == 'solid' and numbers[bid] not in range(1, 8)) or (config.target_group == 'stripe' and numbers[bid] not in range(9, 16))]
        reason = '额外落袋球涉及黑 8、对方球或未确认球' if illegal else ''
    return first, target_pocketed, cue_pocketed, not bool(reason), reason or '模型中进球且通过首碰/母球落袋等基础检查'
