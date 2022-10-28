use clap::Parser;
//use plotly::{ImageFormat, Plot};
use std::cmp;
use std::fs::File;
use std::io::Write;
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, RwLock};
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
    array: Arc<Vec<RwLock<Vec<f64>>>>,
}

fn main() {
    let mut args = Args::parse();

    let mut array: Vec<RwLock<Vec<f64>>> = vec![];
    let mut handles = vec![];
    let mut senders_l: Vec<Sender<f64>> = vec![];
    let mut receivers_l: Vec<Receiver<f64>> = vec![];
    let mut senders_r: Vec<Sender<f64>> = vec![];
    let mut receivers_r: Vec<Receiver<f64>> = vec![];

    args.threads = if args.threads > 0 {
        cmp::min(args.threads, args.a - 2)
    } else {
        available_parallelism().unwrap().get()
    };

    for _ in 0..args.a {
        let col: Vec<f64> = vec![0f64; args.a];
        array.push(RwLock::new(col));
    }
    let arc_array = Arc::new(array);

    for _ in 0..args.threads {
        let (tx_l, rx_l): (Sender<f64>, Receiver<f64>) = mpsc::channel();
        let (tx_r, rx_r): (Sender<f64>, Receiver<f64>) = mpsc::channel();
        senders_l.push(tx_l);
        receivers_l.push(rx_l);
        senders_r.push(tx_r);
        receivers_r.push(rx_r);
    }
    receivers_l.rotate_left(1);
    receivers_r.rotate_right(1);

    let start = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();
    for i in 0..args.threads {
        let task = Task {
            id: i + 1,
            array: Arc::clone(&arc_array),
            txl: senders_l.pop().unwrap(),
            rxl: receivers_l.pop().unwrap(),
            txr: senders_r.pop().unwrap(),
            rxr: receivers_r.pop().unwrap(),
        };

        let handle = thread::spawn(move || compute_column(task, args));
        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }

    let end = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();

    println!("{}", end - start);

    if args.save {
        let result = arc_array
            .iter()
            .map(|rw| rw.read().unwrap().to_vec())
            .collect::<Vec<Vec<f64>>>();

        show_results(result);
    }
}

fn compute_column(task: Task, args: Args) {
    for i in 0..args.iterations {
        let mut x = task.id;
        while x < args.a - 1 {
            for y in 1..args.a - 1 {
                let left = if x != 1 {
                    task.rxl.recv().unwrap()
                } else {
                    0f64
                };
                let right = if i != 0 && x != args.a - 2 {
                    task.rxr.recv().unwrap()
                } else {
                    0f64
                };
                let mut col = task.array[x].write().unwrap();
                col[y] = (args.p / args.T + col[y - 1] + left + col[y + 1] + right) / 4.0;
                if x != args.a - 2 {
                    task.txl.send(col[y]).unwrap();
                }
                if x != 1 {
                    match task.txr.send(col[y]) {
                        _ => continue,
                    };
                }
            }
            x += args.threads;
        }
    }
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
