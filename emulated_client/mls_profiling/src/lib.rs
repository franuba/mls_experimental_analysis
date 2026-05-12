use cpu_time::ThreadTime;
use std::cell::RefCell;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Profiler {
    pub times_ns: HashMap<&'static str, u128>,
}

impl Profiler {
    pub fn new() -> Self {
        Self { times_ns: HashMap::new() }
    }

    fn add(&mut self, key: &'static str, val: u128) {
        *self.times_ns.entry(key).or_insert(0) += val;
    }

    pub fn get(&self, key: &'static str) -> u128 {
        self.times_ns.get(key).cloned().unwrap_or(0)
    }
}
thread_local! {
    static CURRENT: RefCell<Option<Profiler>> = RefCell::new(None);
}

pub fn start_iteration() -> Profiler {
    CURRENT.with(|c| {
        let mut slot = c.borrow_mut();
        let old = slot.take();
        *slot = Some(Profiler::new());
        old.unwrap_or_else(Profiler::new)
    })
}

pub fn record(key: &'static str, value: u128) {
    CURRENT.with(|c| {
        if let Some(ref mut p) = *c.borrow_mut() {
            p.add(key, value);
        }
    });
}

pub struct CpuGuard {
    key: &'static str,
    start: ThreadTime,
}

impl CpuGuard {
    pub fn new(key: &'static str) -> Self {
        Self {
            key,
            start: ThreadTime::now(),
        }
    }
}

impl Drop for CpuGuard {
    fn drop(&mut self) {
        let elapsed = self.start.elapsed().as_micros();
        record(self.key, elapsed);
    }
}

#[macro_export]
macro_rules! track_cpu {
    ($name:expr) => {
        let _g = mls_profiling::CpuGuard::new($name);
    };
}