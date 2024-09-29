# drtv-dl

drtv-dl is a tool for downloading videos from [DRTV](https://dr.dk/drtv) - including its encrypted content.



## Installation

To install drtv-dl, run this:
   ```
   pip install git+https://github.com/444995/drtv-dl.git
   ```
And make sure you have ffmpeg installed on your system.

## Usage

- From the command line:

```
drtv-dl [URL] [OPTIONS]
```

- As a Python module:

```python
import drtv_dl    

drtv_dl.download(
    url="REPLACE_URL", 
    resolution="1080p", 
    with_subs=True
)
```


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


## License

This project is licensed under the MIT License.


## Disclaimer

This tool is for educational purposes only. Please respect the copyright and terms of service of [DRTV](https://dr.dk/drtv). The developers of this tool are not responsible for any misuse or legal consequences.
