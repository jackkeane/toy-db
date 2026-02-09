#pragma once

#include "page.hpp"
#include <string>
#include <fstream>
#include <vector>
#include <cstdint>

namespace toydb {

/**
 * Write-Ahead Log (WAL)
 * 
 * Ensures durability and enables crash recovery by logging all
 * modifications before they are applied to the database.
 * 
 * WAL Protocol:
 * 1. Write operation to log
 * 2. Flush log to disk
 * 3. Apply operation to database
 * 4. Checkpoint periodically
 */
class WAL {
public:
    // WAL record types
    enum class RecordType : uint8_t {
        INSERT = 1,
        UPDATE = 2,
        DELETE = 3,
        CHECKPOINT = 4,
        BEGIN_TXN = 5,
        COMMIT_TXN = 6,
        ABORT_TXN = 7
    };
    
    // WAL record structure
    struct WALRecord {
        RecordType type;
        uint64_t lsn;          // Log Sequence Number (monotonic)
        uint64_t txn_id;       // Transaction ID
        PageID page_id;        // Page being modified
        std::string key;       // Key being modified
        std::string value;     // New value (for INSERT/UPDATE)
        uint32_t checksum;     // CRC32 checksum
        
        WALRecord() 
            : type(RecordType::INSERT), 
              lsn(0), 
              txn_id(0), 
              page_id(INVALID_PAGE_ID),
              checksum(0) {}
    };
    
    explicit WAL(const std::string& wal_file);
    ~WAL();
    
    // Log operations
    uint64_t LogInsert(uint64_t txn_id, PageID page_id, 
                       const std::string& key, const std::string& value);
    uint64_t LogUpdate(uint64_t txn_id, PageID page_id,
                       const std::string& key, const std::string& value);
    uint64_t LogDelete(uint64_t txn_id, PageID page_id,
                       const std::string& key);
    
    // Transaction operations
    uint64_t LogBeginTxn(uint64_t txn_id);
    uint64_t LogCommitTxn(uint64_t txn_id);
    uint64_t LogAbortTxn(uint64_t txn_id);
    
    // Checkpoint
    uint64_t LogCheckpoint();
    
    // Force log to disk
    void Flush();
    
    // Recovery
    std::vector<WALRecord> ReadLog();
    uint64_t GetLastLSN() const { return current_lsn_; }
    
    // Truncate log (after checkpoint)
    void Truncate();

private:
    std::string wal_file_;
    std::fstream log_;
    uint64_t current_lsn_;
    
    // Internal logging
    uint64_t WriteRecord(const WALRecord& record);
    
    // Compute checksum
    uint32_t ComputeChecksum(const WALRecord& record);
    
    // Serialize/deserialize records
    void SerializeRecord(const WALRecord& record, std::vector<char>& buffer);
    bool DeserializeRecord(const std::vector<char>& buffer, WALRecord& record);
};

} // namespace toydb
