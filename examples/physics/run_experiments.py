"""Run upstream-inspired experiments; write CSV/JSON, optionally plot with MPL."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from eight_ball_devtool.computation.experiments import thirty_degree_experiment, straight_shot_experiment


def main():
    parser = argparse.ArgumentParser(description='pooltool 30 度规则 / 直线击球难度实验')
    parser.add_argument('experiment', choices=['30-degree', 'straight-shot'])
    parser.add_argument('--output', type=Path, default=ROOT/'runtime/physics-experiments')
    parser.add_argument('--trials', type=int, default=100)
    parser.add_argument('--positions', type=int, default=12)
    parser.add_argument('--errors', type=float, nargs='+', default=[.15, .25, .5])
    parser.add_argument('--distance', type=float, default=2)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--speed', type=float, default=2.5)
    parser.add_argument('--cuts', type=float, nargs='+', default=[14, 20, 30, 40, 49])
    parser.add_argument('--plot', action='store_true', help='安装 matplotlib 后保存 PNG 图表')
    args = parser.parse_args()
    try:
        rows = thirty_degree_experiment(args.cuts, args.speed) if args.experiment == '30-degree' else straight_shot_experiment(args.distance, args.positions, args.trials, tuple(args.errors), args.seed)
        args.output.mkdir(parents=True, exist_ok=True)
        prefix = args.output/args.experiment
        with prefix.with_suffix('.csv').open('w', encoding='utf-8-sig', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        prefix.with_suffix('.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        if args.plot:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8, 5), layout='constrained')
            if args.experiment == '30-degree':
                ax.plot([r['cut_deg'] for r in rows], [r['measured_carom_deg'] for r in rows], 'o-', label='pooltool')
                ax.plot([r['cut_deg'] for r in rows], [r['theory_carom_deg'] for r in rows], '--', label='Ideal rolling theory')
                ax.set(xlabel='Cut angle (degrees)', ylabel='Carom angle (degrees)')
            else:
                for error in sorted({r['direction_error_deg'] for r in rows}):
                    part = [r for r in rows if r['direction_error_deg'] == error]
                    ax.plot([r['d_over_D'] for r in part], [r['pot_rate'] for r in part], 'o-', label=f'Uniform error ±{error}°')
                ax.set(xlabel='d / D', ylabel='Simulated pot fraction', ylim=(0, 1.05))
            ax.grid(alpha=.3)
            ax.legend()
            fig.savefig(prefix.with_suffix('.png'), dpi=180)
            plt.close(fig)
        print(json.dumps(rows, indent=2))
        print(f'输出：{prefix}.csv / .json')
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f'实验失败：{error}\n')


if __name__ == '__main__':
    main()
