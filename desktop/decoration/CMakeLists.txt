# OziOS window frames: a KDecoration3 plugin for KWin.
#
#   cmake -B build -DCMAKE_INSTALL_PREFIX=/usr && cmake --build build && cmake --install build
#
# Only the public KDecoration3 API is used, so the plugin keeps working while that
# library keeps its interface; if it ever fails to load, KWin falls back to Breeze.
cmake_minimum_required(VERSION 3.22)
project(ozios-decoration VERSION 0.3.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(ECM 6.0 REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})
include(KDEInstallDirs)
include(KDECMakeSettings)

find_package(Qt6 6.6 REQUIRED COMPONENTS Core Gui)
find_package(KF6 6.0 REQUIRED COMPONENTS CoreAddons Config)
find_package(KDecoration3 REQUIRED)

add_library(org.ozios.decoration MODULE
    ozidecoration.cpp
    ozibutton.cpp
    ozishadow.cpp
)
target_compile_definitions(org.ozios.decoration PRIVATE QT_NO_CAST_FROM_ASCII QT_NO_KEYWORDS)
target_link_libraries(org.ozios.decoration PRIVATE
    Qt6::Core
    Qt6::Gui
    KF6::CoreAddons
    KF6::ConfigCore
    KDecoration3::KDecoration
)
set_target_properties(org.ozios.decoration PROPERTIES PREFIX "")
install(TARGETS org.ozios.decoration DESTINATION ${KDE_INSTALL_PLUGINDIR}/org.kde.kdecoration3)
