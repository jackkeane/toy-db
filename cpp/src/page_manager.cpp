#include "page_manager.hpp"
#include <stdexcept>
#include <iostream>

namespace toydb {

PageManager::PageManager(const std::string& db_file) 
    : db_file_(db_file), next_page_id_(1) {
    OpenOrCreateFile();
}

PageManager::~PageManager() {
    FlushAll();
    if (file_.is_open()) {
        file_.close();
    }
}

void PageManager::OpenOrCreateFile() {
    // Try to open existing file
    file_.open(db_file_, std::ios::in | std::ios::out | std::ios::binary);
    
    if (!file_.is_open()) {
        // File doesn't exist, create it
        file_.open(db_file_, std::ios::out | std::ios::binary);
        file_.close();
        
        // Re-open in read/write mode
        file_.open(db_file_, std::ios::in | std::ios::out | std::ios::binary);
        
        if (!file_.is_open()) {
            throw std::runtime_error("Failed to create database file: " + db_file_);
        }
        
        next_page_id_ = 1;
    } else {
        // File exists, determine next page ID
        file_.seekg(0, std::ios::end);
        size_t file_size = file_.tellg();
        next_page_id_ = (file_size / PAGE_SIZE) + 1;
        
        if (next_page_id_ == 1 && file_size > 0) {
            // Corrupted file or wrong page size
            std::cerr << "Warning: Database file size mismatch" << std::endl;
        }
    }
}

PageID PageManager::AllocatePage() {
    PageID new_id = next_page_id_++;
    
    // Create new page
    auto page = std::make_shared<Page>(new_id);
    page->SetPageType(1);  // Data page
    
    // Add to cache
    cache_[new_id] = page;
    
    return new_id;
}

std::shared_ptr<Page> PageManager::ReadPage(PageID page_id) {
    if (page_id == INVALID_PAGE_ID || page_id >= next_page_id_) {
        return nullptr;
    }
    
    // Check cache first
    auto it = cache_.find(page_id);
    if (it != cache_.end()) {
        return it->second;
    }
    
    // Read from disk
    auto page = std::make_shared<Page>(page_id);
    
    file_.seekg((page_id - 1) * PAGE_SIZE, std::ios::beg);
    file_.read(page->GetData(), PAGE_SIZE);
    
    if (!file_.good() && !file_.eof()) {
        throw std::runtime_error("Failed to read page " + std::to_string(page_id));
    }
    
    // If we read less than PAGE_SIZE, the page might not exist yet
    if (file_.gcount() < PAGE_SIZE) {
        // Initialize as new page
        page->Reset();
        page->SetPageID(page_id);
        page->SetPageType(1);
    } else {
        // Successfully read from disk - sync header from data
        page->SyncHeaderFromData();
    }
    
    // Add to cache
    cache_[page_id] = page;
    
    return page;
}

bool PageManager::WritePage(const std::shared_ptr<Page>& page) {
    if (!page || page->GetPageID() == INVALID_PAGE_ID) {
        return false;
    }
    
    PageID page_id = page->GetPageID();
    
    // Seek to page position
    file_.seekp((page_id - 1) * PAGE_SIZE, std::ios::beg);
    
    // Write page data
    file_.write(page->GetData(), PAGE_SIZE);
    file_.flush();
    
    if (!file_.good()) {
        std::cerr << "Failed to write page " << page_id << std::endl;
        return false;
    }
    
    return true;
}

void PageManager::FlushAll() {
    for (const auto& [page_id, page] : cache_) {
        WritePage(page);
    }
    
    if (file_.is_open()) {
        file_.flush();
    }
}

} // namespace toydb
