-- phpMyAdmin SQL Dump
-- version 3.4.5
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Erstellungszeit: 16. Dez 2011 um 15:57
-- Server Version: 5.1.43
-- PHP-Version: 5.2.12-nmm2

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Datenbank: `d0126c4e`
--

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `TUDChat_action`
--

CREATE TABLE IF NOT EXISTS `TUDChat_action` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `chat_uid` varchar(255) NOT NULL,
  `date` datetime NOT NULL,
  `user` varchar(255) NOT NULL,
  `action` enum('add_message','edit_message','delete_message','open_chat','close_chat','ban_user','unban_user') NOT NULL,
  `content` text NOT NULL,
  `target` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `chat_uid` (`chat_uid`)
) ENGINE=MyISAM  DEFAULT CHARSET=latin1 AUTO_INCREMENT=9 ;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
