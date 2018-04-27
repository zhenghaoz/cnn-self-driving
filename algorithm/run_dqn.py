import dqn
from dqn_utils import *
from env import Env
from net import build_mlp, build_cnn


def dqn_learn(env, session, num_iterations, q_func, ep_len, output):
    lr_multiplier = 1.0
    lr_schedule = PiecewiseSchedule([
                                         (0,                   1e-4 * lr_multiplier),
                                         (num_iterations / 10, 1e-4 * lr_multiplier),
                                         (num_iterations / 2,  5e-5 * lr_multiplier),
                                    ],
                                    outside_value=5e-5 * lr_multiplier)
    optimizer = dqn.OptimizerSpec(
        constructor=tf.train.AdamOptimizer,
        kwargs=dict(epsilon=1e-4),
        lr_schedule=lr_schedule
    )

    exploration_schedule = PiecewiseSchedule(
        [
            (0, 1.0),
            (1e6, 0.1),
            (num_iterations / 2, 0.01),
        ], outside_value=0.01
    )

    dqn.learn(
        env,
        q_func=q_func,
        optimizer_spec=optimizer,
        session=session,
        exploration=exploration_schedule,
        replay_buffer_size=100000,
        batch_size=32,
        gamma=0.99,
        learning_starts=50000,
        learning_freq=4,
        frame_history_len=1,
        target_update_freq=10000,
        grad_norm_clipping=10,
        num_iterations=num_iterations,
        log_steps=10000,
        ep_len=ep_len,
        output=output
    )


def get_available_gpus():
    from tensorflow.python.client import device_lib
    local_device_protos = device_lib.list_local_devices()
    return [x.physical_device_desc for x in local_device_protos if x.device_type == 'GPU']


def set_global_seeds(seed):
    tf.set_random_seed(seed)
    np.random.seed(seed)
    random.seed(seed)


def get_session():
    tf.reset_default_graph()
    tf_config = tf.ConfigProto(
        inter_op_parallelism_threads=1,
        intra_op_parallelism_threads=1)
    session = tf.Session(config=tf_config)
    print("AVAILABLE GPUS: ", get_available_gpus())
    return session


def main():
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--obs', type=str, default='Image')
    parser.add_argument('--n_iter', type=int, default=int(5e6))
    parser.add_argument('--ep_len', type=str, default=1000)
    parser.add_argument('--output', '-o', type=str)
    args = parser.parse_args()

    # Set global random seed
    set_global_seeds(args.seed)
    # Create environment
    env = Env(args.obs)
    # Create session
    session = get_session()
    # Start deep Q learning
    if args.obs == 'Image':
        q_func = build_cnn
    elif args.obs == 'Distance':
        q_func = build_mlp
    else:
        raise ValueError('Unsupported observation ' + args.obs)
    dqn_learn(env, session, num_iterations=args.n_iter, q_func=q_func, ep_len=args.ep_len, output=args.output)


if __name__ == "__main__":
    main()
