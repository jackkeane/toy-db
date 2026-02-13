#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "page.hpp"
#include "page_manager.hpp"
#include "buffer_pool.hpp"
#include "btree.hpp"
#include "wal.hpp"
#include <atomic>
#include <set>
#include <algorithm>
#include <unordered_map>
#include <vector>

namespace py = pybind11;
using namespace toydb;

/**
 * Simple key-value storage interface
 * Stores key-value pairs across pages
 */
class StorageEngine {
public:
    explicit StorageEngine(const std::string& db_file) 
        : page_manager_(db_file),
          buffer_pool_(128, &page_manager_) {
        
        // Try to read existing metadata page or allocate new one
        if (page_manager_.GetNumPages() > 1) {
            // Database exists, load metadata page
            metadata_page_id_ = 1;
            auto page = buffer_pool_.FetchPage(metadata_page_id_);
            if (page) {
                // Restore offset from page header
                current_offset_ = page->GetHeader().free_space_offset;
            }
        } else {
            // New database, allocate first page
            metadata_page_id_ = page_manager_.AllocatePage();
        }
    }
    
    void insert(const std::string& key, const std::string& value) {
        // Simple implementation: store in first available space
        // For now, just store in metadata page
        auto page = buffer_pool_.FetchPage(metadata_page_id_);
        if (!page) {
            throw std::runtime_error("Failed to fetch page");
        }
        
        // Store key-value pair (simplified - no real structure yet)
        // Use \x1E (record separator) and \x1F (unit separator) as delimiters
        std::string record = key + "\x1E" + value + "\x1F";
        
        // Update offset BEFORE writing so header is correct
        current_offset_ += record.size();
        page->GetHeader().free_space_offset = current_offset_;
        
        // Now write data (this will also sync the header to the buffer)
        page->WriteData(current_offset_ - record.size(), record.c_str(), record.size());
        
        buffer_pool_.MarkDirty(metadata_page_id_);
    }
    
    std::string get(const std::string& key) {
        auto page = buffer_pool_.FetchPage(metadata_page_id_);
        if (!page) {
            throw std::runtime_error("Failed to fetch page");
        }
        
        // Read all data and parse (very inefficient, but simple)
        char buffer[PAGE_SIZE];
        size_t data_start = sizeof(Page::Header);
        size_t data_len = current_offset_ - data_start;
        page->ReadData(data_start, buffer, data_len);
        
        std::string data(buffer, data_len);
        
        // Parse key-value pairs (using \x1E and \x1F as delimiters)
        size_t pos = 0;
        while (pos < data.size()) {
            size_t sep1 = data.find('\x1E', pos);  // Record separator
            size_t sep2 = data.find('\x1F', pos);  // Unit separator
            
            if (sep1 == std::string::npos || sep2 == std::string::npos) {
                break;
            }
            
            std::string k = data.substr(pos, sep1 - pos);
            std::string v = data.substr(sep1 + 1, sep2 - sep1 - 1);
            
            if (k == key) {
                return v;
            }
            
            pos = sep2 + 1;
        }
        
        throw std::runtime_error("Key not found: " + key);
    }
    
    void flush() {
        buffer_pool_.FlushDirty();
    }
    
    double get_cache_hit_rate() const {
        return buffer_pool_.GetHitRate();
    }

private:
    PageManager page_manager_;
    BufferPool buffer_pool_;
    PageID metadata_page_id_;
    size_t current_offset_ = sizeof(Page::Header);
};

/**
 * Transaction-aware storage engine with WAL
 */
class TransactionalStorageEngine {
public:
    explicit TransactionalStorageEngine(const std::string& db_file)
        : page_manager_(db_file),
          buffer_pool_(128, &page_manager_),
          btree_(&buffer_pool_, &page_manager_),
          wal_(db_file + ".wal"),
          next_txn_id_(1) {

        // Check if database exists and has a root node
        if (page_manager_.GetNumPages() > 1) {
            // Existing database - open the B-Tree
            btree_.OpenTree(1);
        } else {
            // New database - create B-Tree
            btree_.CreateTree();
        }

        // Check if we need recovery
        auto wal_records = wal_.ReadLog();

        if (!wal_records.empty()) {
            // Perform recovery
            Recover(wal_records);
        }
    }
    
    ~TransactionalStorageEngine() {
        // Final checkpoint
        wal_.LogCheckpoint();
        wal_.Flush();
        buffer_pool_.FlushDirty();
    }
    
    uint64_t begin_transaction() {
        uint64_t txn_id = next_txn_id_++;
        wal_.LogBeginTxn(txn_id);
        wal_.Flush();
        return txn_id;
    }
    
    void commit_transaction(uint64_t txn_id) {
        wal_.LogCommitTxn(txn_id);
        wal_.Flush();
        buffer_pool_.FlushDirty();
        txn_inserts_.erase(txn_id);
    }
    
    void abort_transaction(uint64_t txn_id) {
        // Best-effort rollback for inserts in this transaction.
        // (UPDATE/DELETE rollback requires before-images and is not yet implemented.)
        auto it = txn_inserts_.find(txn_id);
        if (it != txn_inserts_.end()) {
            for (const auto& key : it->second) {
                btree_.Delete(key);
            }
            txn_inserts_.erase(it);
        }

        wal_.LogAbortTxn(txn_id);
        wal_.Flush();
        buffer_pool_.FlushDirty();
    }
    
    void insert(const std::string& key, const std::string& value) {
        insert_txn(0, key, value);  // Auto-txn
    }
    
    void insert_txn(uint64_t txn_id, const std::string& key, const std::string& value) {
        bool auto_txn = (txn_id == 0);
        
        if (auto_txn) {
            txn_id = begin_transaction();
        }
        
        // Log the operation
        wal_.LogInsert(txn_id, 1, key, value);
        wal_.Flush();
        
        // Apply to B-Tree
        btree_.Insert(key, value);

        if (!auto_txn) {
            txn_inserts_[txn_id].push_back(key);
        }
        
        if (auto_txn) {
            commit_transaction(txn_id);
        }
    }

    void remove(const std::string& key) {
        remove_txn(0, key);  // Auto-txn
    }

    void remove_txn(uint64_t txn_id, const std::string& key) {
        bool auto_txn = (txn_id == 0);

        if (auto_txn) {
            txn_id = begin_transaction();
        }

        // Log the operation
        wal_.LogDelete(txn_id, 1, key);
        wal_.Flush();

        // Apply to B-Tree
        bool deleted = btree_.Delete(key);
        if (!deleted) {
            throw std::runtime_error("Key not found: " + key);
        }

        if (auto_txn) {
            commit_transaction(txn_id);
        }
    }
    
    std::string get(const std::string& key) {
        auto result = btree_.Search(key);
        if (result.has_value()) {
            return result.value();
        }
        throw std::runtime_error("Key not found: " + key);
    }
    
    std::vector<std::pair<std::string, std::string>> range_scan(
        const std::string& start_key,
        const std::string& end_key
    ) {
        return btree_.RangeScan(start_key, end_key);
    }
    
    void checkpoint() {
        wal_.LogCheckpoint();
        buffer_pool_.FlushDirty();
        wal_.Flush();
        
        // After checkpoint, we can truncate the WAL
        wal_.Truncate();
    }
    
    void flush() {
        buffer_pool_.FlushDirty();
        wal_.Flush();
    }
    
    double get_cache_hit_rate() const {
        return buffer_pool_.GetHitRate();
    }
    
    uint64_t get_last_lsn() const {
        return wal_.GetLastLSN();
    }

private:
    PageManager page_manager_;
    BufferPool buffer_pool_;
    BTree btree_;
    WAL wal_;
    std::atomic<uint64_t> next_txn_id_;
    std::unordered_map<uint64_t, std::vector<std::string>> txn_inserts_;
    
    void Recover(const std::vector<WAL::WALRecord>& records) {
        // Replay all durable operations:
        // - auto transactions (txn_id == 0)
        // - committed explicit transactions
        std::set<uint64_t> committed_txns;
        std::set<uint64_t> aborted_txns;

        // First pass: find committed and aborted transactions
        for (const auto& record : records) {
            if (record.type == WAL::RecordType::COMMIT_TXN) {
                committed_txns.insert(record.txn_id);
            } else if (record.type == WAL::RecordType::ABORT_TXN) {
                aborted_txns.insert(record.txn_id);
            }
        }

        // Start replay after the last checkpoint (if any)
        size_t replay_start = 0;
        for (size_t i = 0; i < records.size(); ++i) {
            if (records[i].type == WAL::RecordType::CHECKPOINT) {
                replay_start = i + 1;
            }
        }

        for (size_t i = replay_start; i < records.size(); ++i) {
            const auto& record = records[i];

            bool durable = (record.txn_id == 0) ||
                           (committed_txns.count(record.txn_id) && !aborted_txns.count(record.txn_id));
            if (!durable) {
                continue;
            }

            if (record.type == WAL::RecordType::INSERT ||
                record.type == WAL::RecordType::UPDATE) {
                btree_.Insert(record.key, record.value);
            } else if (record.type == WAL::RecordType::DELETE) {
                btree_.Delete(record.key);
            }
        }

        // Update next transaction ID
        uint64_t max_txn_id = 0;
        for (const auto& record : records) {
            max_txn_id = std::max(max_txn_id, record.txn_id);
        }
        next_txn_id_ = max_txn_id + 1;
    }
};

/**
 * Indexed storage engine using B-Tree
 */
class IndexedStorageEngine {
public:
    explicit IndexedStorageEngine(const std::string& db_file)
        : page_manager_(db_file),
          buffer_pool_(128, &page_manager_),
          btree_(&buffer_pool_, &page_manager_) {
        
        // Check if database exists and has a root node
        if (page_manager_.GetNumPages() > 1) {
            // Existing database - open the B-Tree (root is always page 1)
            btree_.OpenTree(1);
        } else {
            // New database - create B-Tree
            btree_.CreateTree();
        }
    }
    
    void insert(const std::string& key, const std::string& value) {
        btree_.Insert(key, value);
    }

    void remove(const std::string& key) {
        bool deleted = btree_.Delete(key);
        if (!deleted) {
            throw std::runtime_error("Key not found: " + key);
        }
    }
    
    std::string get(const std::string& key) {
        auto result = btree_.Search(key);
        if (result.has_value()) {
            return result.value();
        }
        throw std::runtime_error("Key not found: " + key);
    }
    
    std::vector<std::pair<std::string, std::string>> range_scan(
        const std::string& start_key,
        const std::string& end_key
    ) {
        return btree_.RangeScan(start_key, end_key);
    }
    
    void flush() {
        buffer_pool_.FlushDirty();
    }
    
    double get_cache_hit_rate() const {
        return buffer_pool_.GetHitRate();
    }

private:
    PageManager page_manager_;
    BufferPool buffer_pool_;
    BTree btree_;
};

PYBIND11_MODULE(_storage_engine, m) {
    m.doc() = "ToyDB Storage Engine - C++ backend for database storage";
    
    // Simple linear storage (Phase 1)
    py::class_<StorageEngine>(m, "StorageEngine")
        .def(py::init<const std::string&>())
        .def("insert", &StorageEngine::insert, 
             "Insert a key-value pair",
             py::arg("key"), py::arg("value"))
        .def("get", &StorageEngine::get,
             "Get value by key",
             py::arg("key"))
        .def("flush", &StorageEngine::flush,
             "Flush all dirty pages to disk")
        .def("get_cache_hit_rate", &StorageEngine::get_cache_hit_rate,
             "Get buffer pool cache hit rate");
    
    // B-Tree indexed storage (Phase 2)
    py::class_<IndexedStorageEngine>(m, "IndexedStorageEngine")
        .def(py::init<const std::string&>())
        .def("insert", &IndexedStorageEngine::insert,
             "Insert a key-value pair into B-Tree",
             py::arg("key"), py::arg("value"))
        .def("delete", &IndexedStorageEngine::remove,
             "Delete a key-value pair from B-Tree",
             py::arg("key"))
        .def("get", &IndexedStorageEngine::get,
             "Get value by key from B-Tree",
             py::arg("key"))
        .def("range_scan", &IndexedStorageEngine::range_scan,
             "Scan keys in range [start_key, end_key]",
             py::arg("start_key"), py::arg("end_key"))
        .def("flush", &IndexedStorageEngine::flush,
             "Flush all dirty pages to disk")
        .def("get_cache_hit_rate", &IndexedStorageEngine::get_cache_hit_rate,
             "Get buffer pool cache hit rate");
    
    // Transactional storage with WAL (Phase 3)
    py::class_<TransactionalStorageEngine>(m, "TransactionalStorageEngine")
        .def(py::init<const std::string&>())
        .def("begin_transaction", &TransactionalStorageEngine::begin_transaction,
             "Begin a new transaction, returns transaction ID")
        .def("commit_transaction", &TransactionalStorageEngine::commit_transaction,
             "Commit a transaction",
             py::arg("txn_id"))
        .def("abort_transaction", &TransactionalStorageEngine::abort_transaction,
             "Abort a transaction",
             py::arg("txn_id"))
        .def("insert", &TransactionalStorageEngine::insert,
             "Insert with auto-transaction",
             py::arg("key"), py::arg("value"))
        .def("insert_txn", &TransactionalStorageEngine::insert_txn,
             "Insert within a transaction",
             py::arg("txn_id"), py::arg("key"), py::arg("value"))
        .def("delete", &TransactionalStorageEngine::remove,
             "Delete with auto-transaction",
             py::arg("key"))
        .def("delete_txn", &TransactionalStorageEngine::remove_txn,
             "Delete within a transaction",
             py::arg("txn_id"), py::arg("key"))
        .def("get", &TransactionalStorageEngine::get,
             "Get value by key",
             py::arg("key"))
        .def("range_scan", &TransactionalStorageEngine::range_scan,
             "Scan keys in range [start_key, end_key]",
             py::arg("start_key"), py::arg("end_key"))
        .def("checkpoint", &TransactionalStorageEngine::checkpoint,
             "Create checkpoint and truncate WAL")
        .def("flush", &TransactionalStorageEngine::flush,
             "Flush all changes to disk")
        .def("get_cache_hit_rate", &TransactionalStorageEngine::get_cache_hit_rate,
             "Get buffer pool cache hit rate")
        .def("get_last_lsn", &TransactionalStorageEngine::get_last_lsn,
             "Get last log sequence number");
}
