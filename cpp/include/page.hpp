#pragma once

#include <cstdint>
#include <cstring>
#include <memory>

namespace toydb {

// Page size: 4KB (common database page size)
constexpr size_t PAGE_SIZE = 4096;

// Page ID type
using PageID = uint32_t;
constexpr PageID INVALID_PAGE_ID = 0;

/**
 * Page - Fixed-size unit of storage (4KB)
 * 
 * Layout:
 *   [Header: 16 bytes]
 *   [Data: 4080 bytes]
 */
class Page {
public:
    // Page header
    struct Header {
        PageID page_id;          // Page identifier
        uint16_t page_type;      // Type: 0=Free, 1=Data, 2=Index
        uint16_t num_slots;      // Number of data slots used
        uint32_t free_space_offset;  // Offset to start of free space
        uint32_t checksum;       // Optional: data integrity check
    };

    Page();
    explicit Page(PageID id);
    ~Page() = default;

    // Accessors
    PageID GetPageID() const { return header_.page_id; }
    void SetPageID(PageID id) { header_.page_id = id; }
    
    uint16_t GetPageType() const { return header_.page_type; }
    void SetPageType(uint16_t type) { header_.page_type = type; }

    // Get raw data pointer (for I/O operations)
    char* GetData() { return data_.get(); }
    const char* GetData() const { return data_.get(); }

    // Get header
    Header& GetHeader() { return header_; }
    const Header& GetHeader() const { return header_; }

    // Reset page to initial state
    void Reset();
    
    // Sync header from data buffer (call after loading from disk)
    void SyncHeaderFromData();

    // Copy data to page
    bool WriteData(size_t offset, const char* src, size_t len);
    
    // Read data from page
    bool ReadData(size_t offset, char* dest, size_t len) const;

private:
    Header header_;
    std::unique_ptr<char[]> data_;  // 4KB data buffer
};

} // namespace toydb
