use bytes::{Buf, BufMut, BytesMut};
use std::io;
use tokio_util::codec::{Decoder, Encoder};

#[derive(Debug, Clone)]
pub struct LengthPrefixedCodec {
    max_message_bytes: usize,
}

impl LengthPrefixedCodec {
    pub fn new(max_message_bytes: usize) -> Self {
        Self { max_message_bytes }
    }
}

impl Decoder for LengthPrefixedCodec {
    type Item = Vec<u8>;
    type Error = io::Error;

    fn decode(&mut self, src: &mut BytesMut) -> Result<Option<Self::Item>, Self::Error> {
        if src.len() < 4 {
            return Ok(None);
        }

        let mut length_bytes = [0u8; 4];
        length_bytes.copy_from_slice(&src[..4]);
        let length = u32::from_be_bytes(length_bytes) as usize;

        if length > self.max_message_bytes {
            src.advance(src.len()); // discard malformed/oversized buffer
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!(
                    "Frame size {} exceeds maximum allowed limit {}",
                    length, self.max_message_bytes
                ),
            ));
        }

        if src.len() < 4 + length {
            src.reserve(4 + length - src.len());
            return Ok(None);
        }

        src.advance(4);
        let data = src.split_to(length).to_vec();
        Ok(Some(data))
    }
}

impl Encoder<Vec<u8>> for LengthPrefixedCodec {
    type Error = io::Error;

    fn encode(&mut self, item: Vec<u8>, dst: &mut BytesMut) -> Result<(), Self::Error> {
        let length = item.len();
        if length > self.max_message_bytes {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!(
                    "Outgoing frame size {} exceeds maximum limit {}",
                    length, self.max_message_bytes
                ),
            ));
        }

        dst.reserve(4 + length);
        dst.put_u32(length as u32);
        dst.put_slice(&item);
        Ok(())
    }
}
