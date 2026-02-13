#include "wal.hpp"
#include <cstring>
#include <stdexcept>

namespace toydb {

WAL::WAL(const std::string& wal_file) 
    : wal_file_(wal_file), current_lsn_(0) {
    
    // Try to open existing WAL file
    log_.open(wal_file_, std::ios::in | std::ios::out | std::ios::binary);
    
    if (!log_.is_open()) {
        // Create new file
        std::ofstream create(wal_file_, std::ios::binary);
        create.close();
        
        // Open for read/write
        log_.open(wal_file_, std::ios::in | std::ios::out | std::ios::binary);
        
        if (!log_.is_open()) {
            throw std::runtime_error("Failed to open WAL file: " + wal_file_);
        }
        
        current_lsn_ = 0;
    } else {
        // Existing WAL - read last LSN
        log_.seekg(0, std::ios::end);
        size_t file_size = log_.tellg();
        
        if (file_size > 0) {
            // Read all records to find max LSN
            auto records = ReadLog();
            if (!records.empty()) {
                current_lsn_ = records.back().lsn;
            }
        }
    }
}

WAL::~WAL() {
    if (log_.is_open()) {
        Flush();
        log_.close();
    }
}

uint64_t WAL::LogInsert(uint64_t txn_id, PageID page_id,
                        const std::string& key, const std::string& value) {
    WALRecord record;
    record.type = RecordType::INSERT;
    record.txn_id = txn_id;
    record.page_id = page_id;
    record.key = key;
    record.value = value;
    
    return WriteRecord(record);
}

uint64_t WAL::LogUpdate(uint64_t txn_id, PageID page_id,
                        const std::string& key, const std::string& value) {
    WALRecord record;
    record.type = RecordType::UPDATE;
    record.txn_id = txn_id;
    record.page_id = page_id;
    record.key = key;
    record.value = value;
    
    return WriteRecord(record);
}

uint64_t WAL::LogDelete(uint64_t txn_id, PageID page_id,
                        const std::string& key) {
    WALRecord record;
    record.type = RecordType::DELETE;
    record.txn_id = txn_id;
    record.page_id = page_id;
    record.key = key;
    
    return WriteRecord(record);
}

uint64_t WAL::LogBeginTxn(uint64_t txn_id) {
    WALRecord record;
    record.type = RecordType::BEGIN_TXN;
    record.txn_id = txn_id;
    
    return WriteRecord(record);
}

uint64_t WAL::LogCommitTxn(uint64_t txn_id) {
    WALRecord record;
    record.type = RecordType::COMMIT_TXN;
    record.txn_id = txn_id;
    
    return WriteRecord(record);
}

uint64_t WAL::LogAbortTxn(uint64_t txn_id) {
    WALRecord record;
    record.type = RecordType::ABORT_TXN;
    record.txn_id = txn_id;
    
    return WriteRecord(record);
}

uint64_t WAL::LogCheckpoint() {
    WALRecord record;
    record.type = RecordType::CHECKPOINT;
    record.txn_id = 0;
    
    return WriteRecord(record);
}

uint64_t WAL::WriteRecord(const WALRecord& record_in) {
    WALRecord record = record_in;
    record.lsn = ++current_lsn_;
    record.checksum = ComputeChecksum(record);
    
    std::vector<char> buffer;
    SerializeRecord(record, buffer);
    
    // Append to log
    log_.seekp(0, std::ios::end);
    log_.write(buffer.data(), buffer.size());
    
    return record.lsn;
}

void WAL::Flush() {
    if (log_.is_open()) {
        log_.flush();
    }
}

uint32_t WAL::ComputeChecksum(const WALRecord& record) {
    // Simple checksum: XOR of all bytes
    uint32_t checksum = 0;
    
    checksum ^= static_cast<uint32_t>(record.type);
    checksum ^= static_cast<uint32_t>(record.lsn);
    checksum ^= static_cast<uint32_t>(record.txn_id);
    checksum ^= record.page_id;
    
    for (char c : record.key) {
        checksum ^= static_cast<uint32_t>(c);
    }
    
    for (char c : record.value) {
        checksum ^= static_cast<uint32_t>(c);
    }
    
    return checksum;
}

void WAL::SerializeRecord(const WALRecord& record, std::vector<char>& buffer) {
    // Record format:
    // [type:1] [lsn:8] [txn_id:8] [page_id:4] [key_len:2] [key:N] [val_len:2] [val:M] [checksum:4]
    
    buffer.clear();
    
    // Type
    uint8_t type_byte = static_cast<uint8_t>(record.type);
    buffer.push_back(type_byte);
    
    // LSN
    for (int i = 0; i < 8; ++i) {
        buffer.push_back((record.lsn >> (i * 8)) & 0xFF);
    }
    
    // Transaction ID
    for (int i = 0; i < 8; ++i) {
        buffer.push_back((record.txn_id >> (i * 8)) & 0xFF);
    }
    
    // Page ID
    for (int i = 0; i < 4; ++i) {
        buffer.push_back((record.page_id >> (i * 8)) & 0xFF);
    }
    
    // Key length and data
    uint16_t key_len = record.key.size();
    buffer.push_back(key_len & 0xFF);
    buffer.push_back((key_len >> 8) & 0xFF);
    buffer.insert(buffer.end(), record.key.begin(), record.key.end());
    
    // Value length and data
    uint16_t val_len = record.value.size();
    buffer.push_back(val_len & 0xFF);
    buffer.push_back((val_len >> 8) & 0xFF);
    buffer.insert(buffer.end(), record.value.begin(), record.value.end());
    
    // Checksum
    for (int i = 0; i < 4; ++i) {
        buffer.push_back((record.checksum >> (i * 8)) & 0xFF);
    }
}

bool WAL::DeserializeRecord(const std::vector<char>& buffer, WALRecord& record) {
    if (buffer.size() < 27) {  // Minimum record size
        return false;
    }
    
    size_t offset = 0;
    
    // Type
    record.type = static_cast<RecordType>(buffer[offset++]);
    
    // LSN
    record.lsn = 0;
    for (int i = 0; i < 8; ++i) {
        record.lsn |= (static_cast<uint64_t>(static_cast<uint8_t>(buffer[offset++])) << (i * 8));
    }
    
    // Transaction ID
    record.txn_id = 0;
    for (int i = 0; i < 8; ++i) {
        record.txn_id |= (static_cast<uint64_t>(static_cast<uint8_t>(buffer[offset++])) << (i * 8));
    }
    
    // Page ID
    record.page_id = 0;
    for (int i = 0; i < 4; ++i) {
        record.page_id |= (static_cast<uint32_t>(static_cast<uint8_t>(buffer[offset++])) << (i * 8));
    }
    
    // Key
    uint16_t key_len = static_cast<uint8_t>(buffer[offset]) | 
                      (static_cast<uint8_t>(buffer[offset + 1]) << 8);
    offset += 2;
    
    if (offset + key_len > buffer.size()) {
        return false;
    }
    
    record.key.assign(buffer.begin() + offset, buffer.begin() + offset + key_len);
    offset += key_len;
    
    // Value
    uint16_t val_len = static_cast<uint8_t>(buffer[offset]) | 
                      (static_cast<uint8_t>(buffer[offset + 1]) << 8);
    offset += 2;
    
    if (offset + val_len + 4 > buffer.size()) {
        return false;
    }
    
    record.value.assign(buffer.begin() + offset, buffer.begin() + offset + val_len);
    offset += val_len;
    
    // Checksum
    record.checksum = 0;
    for (int i = 0; i < 4; ++i) {
        record.checksum |= (static_cast<uint32_t>(static_cast<uint8_t>(buffer[offset++])) << (i * 8));
    }
    
    // Verify checksum
    uint32_t computed = ComputeChecksum(record);
    if (computed != record.checksum) {
        return false;  // Corrupted record
    }
    
    return true;
}

std::vector<WAL::WALRecord> WAL::ReadLog() {
    std::vector<WALRecord> records;

    // Reset stream state before reading (important after writes/eof)
    log_.clear();
    log_.seekg(0, std::ios::beg);
    
    while (log_.good() && !log_.eof()) {
        // Read record size (we need to read header first to determine size)
        char header[27];  // Minimum header size
        log_.read(header, 27);
        
        if (log_.gcount() < 27) {
            break;  // End of file or incomplete record
        }
        
        // Get key and value lengths
        uint16_t key_len = static_cast<uint8_t>(header[21]) | 
                          (static_cast<uint8_t>(header[22]) << 8);
        
        // Read key
        std::vector<char> key_buf(key_len);
        log_.read(key_buf.data(), key_len);
        
        if (log_.gcount() < key_len) {
            break;
        }
        
        // Read value length
        char val_len_bytes[2];
        log_.read(val_len_bytes, 2);
        
        if (log_.gcount() < 2) {
            break;
        }
        
        uint16_t val_len = static_cast<uint8_t>(val_len_bytes[0]) | 
                          (static_cast<uint8_t>(val_len_bytes[1]) << 8);
        
        // Read value
        std::vector<char> val_buf(val_len);
        log_.read(val_buf.data(), val_len);
        
        if (log_.gcount() < val_len) {
            break;
        }
        
        // Read checksum
        char checksum_bytes[4];
        log_.read(checksum_bytes, 4);
        
        if (log_.gcount() < 4) {
            break;
        }
        
        // Reconstruct full buffer
        std::vector<char> full_buffer;
        full_buffer.insert(full_buffer.end(), header, header + 27);
        full_buffer.insert(full_buffer.end(), key_buf.begin(), key_buf.end());
        full_buffer.insert(full_buffer.end(), val_len_bytes, val_len_bytes + 2);
        full_buffer.insert(full_buffer.end(), val_buf.begin(), val_buf.end());
        full_buffer.insert(full_buffer.end(), checksum_bytes, checksum_bytes + 4);
        
        WALRecord record;
        if (DeserializeRecord(full_buffer, record)) {
            records.push_back(record);
        } else {
            // Corrupted record, stop reading
            break;
        }
    }
    
    return records;
}

void WAL::Truncate() {
    log_.close();
    
    // Truncate file
    std::ofstream truncate(wal_file_, std::ios::trunc | std::ios::binary);
    truncate.close();
    
    // Reopen
    log_.open(wal_file_, std::ios::in | std::ios::out | std::ios::binary);
    current_lsn_ = 0;
}

} // namespace toydb
