import { Theme, SideNav, SideNavItems, SideNavMenuItem } from '@carbon/react';
import { NavLink } from 'react-router-dom';
import { useRef, useEffect } from 'react';
import styles from './Navbar.module.scss';

const Navbar = ({ isSideNavOpen, setIsSideNavOpen }) => {
  const navRef = useRef(null);

  useEffect(() => {
    function handleOutsideClick(e) {
      if (!isSideNavOpen || !setIsSideNavOpen) return;
      const target = e.target;
      if (navRef.current && navRef.current.contains(target)) return;
      setIsSideNavOpen(false);
    }

    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isSideNavOpen, setIsSideNavOpen]);

  return (
    <Theme theme="g100">
      <SideNav
        aria-label="Side navigation"
        expanded={isSideNavOpen}
        isPersistent={false}
        ref={navRef}
      >
        <SideNavItems>
          <SideNavMenuItem
            as={NavLink}
            to="/upload"
            className={styles.sideNavItem}
          >
            Upload Documents
          </SideNavMenuItem>

          <SideNavMenuItem
            as={NavLink}
            to="/jobs"
            className={styles.sideNavItem}
          >
            Job Monitor
          </SideNavMenuItem>

          <SideNavMenuItem
            as={NavLink}
            to="/documents"
            className={styles.sideNavItem}
          >
            Documents
          </SideNavMenuItem>
        </SideNavItems>
      </SideNav>
    </Theme>
  );
};

export default Navbar;

// Made with Bob
