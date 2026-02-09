#include "page.hpp"
#include <stdexcept>

namespace toydb {

Page::Page() : header_{}, data_(new char[PAGE_SIZE]) {
    Reset();
}

Page::Page(PageID id) : Page() {
    header_.page_id = id;
}

void Page::Reset() {
    header_.page_id = INVALID_PAGE_ID;
    header_.page_type = 0;
    header_.num_slots = 0;
    header_.free_space_offset = sizeof(Header);
    header_.checksum = 0;
    
    // Zero out data
    std::memset(data_.get(), 0, PAGE_SIZE);
    
    // Write header to data buffer
    std::memcpy(data_.get(), &header_, sizeof(Header));
}

void Page::SyncHeaderFromData() {
    // Load header from data buffer (called after reading from disk)
    std::memcpy(&header_, data_.get(), sizeof(Header));
}

bool Page::WriteData(size_t offset, const char* src, size_t len) {
    if (offset + len > PAGE_SIZE) {
        return false;  // Out of bounds
    }
    
    std::memcpy(data_.get() + offset, src, len);
    
    // Update header in data buffer
    std::memcpy(data_.get(), &header_, sizeof(Header));
    
    return true;
}

bool Page::ReadData(size_t offset, char* dest, size_t len) const {
    if (offset + len > PAGE_SIZE) {
        return false;  // Out of bounds
    }
    
    std::memcpy(dest, data_.get() + offset, len);
    return true;
}

} // namespace toydb
