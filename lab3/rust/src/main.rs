use clap::Parser;
//use plotly::{ImageFormat, Plot};
use std::cmp;
use std::fs::File;
use std::io::Write;
use std::sync::mpsc::{self, Receiver, Sender};
use std::thread::{self, available_parallelism};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Parser, Debug, Clone, Copy)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(short, long, default_value_t = 0)]
    threads: usize,
    #[arg(short, long, default_value_t = 1000)]
    iterations: usize,
    #[arg(short, default_value_t = 100)]
    a: usize,
    #[arg(short, default_value_t = 10.0)]
    p: f64,
    #[arg(short = 'T', default_value_t = 10.0)]
    T: f64,
    #[arg(short, long)]
    save: bool,
}

struct Task {
    id: usize,
    txl: Sender<f64>,
    rxl: Receiver<f64>,
    txr: Sender<f64>,
    rxr: Receiver<f64>,
    result_t: Sender<Result>,
}

struct Result {
    id: usize,
    values: Vec<Vec<f64>>,
}

fn main() {
    let mut args = Args::parse();

    args.threads = cmp::min(
        if args.threads > 0 {
            args.threads
        } else {
            available_parallelism().unwrap().get()
        },
        args.a - 2,
    );

    let mut array: Vec<Vec<f64>> = vec![vec![]; args.a];
    let mut senders_l: Vec<Sender<f64>> = vec![];
    let mut receivers_l: Vec<Receiver<f64>> = vec![];
    let mut senders_r: Vec<Sender<f64>> = vec![];
    let mut receivers_r: Vec<Receiver<f64>> = vec![];
    let (results_t, results_r) = mpsc::channel();

    for _ in 0..args.threads {
        let (tx_l, rx_l) = mpsc::channel();
        let (tx_r, rx_r) = mpsc::channel();
        senders_l.push(tx_l);
        receivers_l.push(rx_l);
        senders_r.push(tx_r);
        receivers_r.push(rx_r);
    }
    receivers_l.rotate_left(1);
    receivers_r.rotate_right(1);

    // start measuring time
    let start = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();

    for i in 0..args.threads {
        let task = Task {
            id: i + 1,
            txl: senders_l.pop().unwrap(),
            rxl: receivers_l.pop().unwrap(),
            txr: senders_r.pop().unwrap(),
            rxr: receivers_r.pop().unwrap(),
            result_t: results_t.clone(),
        };

        thread::spawn(move || compute_column(task, args));
    }
    drop(results_t);

    for result in results_r {
        let mut x = result.id;
        for col in result.values {
            array[x] = col;
            x += args.threads;
        }
    }
    array[0] = vec![0f64; args.a];
    array[args.a - 1] = vec![0f64; args.a];

    // end measuring time
    let end = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();

    println!("{}", end - start);

    if args.save {
        show_results(array);
    }
}

fn compute_column(task: Task, args: Args) {
    let n_cols = div_ceil(args.a - 1 - task.id, args.threads);
    let mut array: Vec<Vec<f64>> = vec![vec![0f64; args.a]; n_cols];

    for i in 0..args.iterations {
        for x in 0..n_cols {
            let not_first = !(x == 0 && task.id == 1);
            let not_last = !(task.id + args.threads * x == args.a - 2);
            for y in 1..args.a - 1 {
                let left = if not_first {
                    task.rxl.recv().unwrap()
                } else {
                    0f64
                };
                let right = if i != 0 && not_last {
                    task.rxr.recv().unwrap()
                } else {
                    0f64
                };

                array[x][y] =
                    (args.p / args.T + array[x][y - 1] + left + array[x][y + 1] + right) / 4.0;

                if not_last {
                    task.txl.send(array[x][y]).unwrap();
                }
                if not_first {
                    match task.txr.send(array[x][y]) {
                        _ => continue,
                    };
                }
            }
        }
    }

    task.result_t
        .send(Result {
            id: task.id,
            values: array,
        })
        .unwrap();
}

fn show_results(values: Vec<Vec<f64>>) {
    let mut file = File::create("results.csv").unwrap();
    for row in values.iter() {
        let strings: Vec<String> = row.iter().map(|n| n.to_string()).collect();
        writeln!(file, "{}", strings.join(", ")).unwrap();
    }
    // let trace = HeatMap::new_z(values);
    // let mut plot = Plot::new();
    // plot.add_trace(trace);
    // plot.save("./result.png", ImageFormat::PNG, 400, 400, 1.0);
}

fn div_ceil(a: usize, b: usize) -> usize {
    return a / b + usize::from(a % b != 0);
}
