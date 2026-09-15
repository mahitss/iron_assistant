fn main() {
    #[cfg(windows)]
    {
        println!("cargo:rustc-link-lib=crypt32");
        println!("cargo:rustc-link-lib=secur32");
        println!("cargo:rustc-link-lib=advapi32");
        println!("cargo:rustc-link-lib=ncrypt");
    }
}
