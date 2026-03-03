import { Theme, SideNav, SideNavItems, SideNavLink } from '@carbon/react';
import { Upload, Activity, Document } from '@carbon/icons-react';
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
    <Theme theme="white">
      <SideNav
        aria-label="Side navigation"
        expanded={isSideNavOpen}
        isFixedNav
        isChildOfHeader={false}
        ref={navRef}
      >
        <SideNavItems>
          <SideNavLink
            renderIcon={Upload}
            as={NavLink}
            to="/upload"
            className={styles.sideNavItem}
          >
            Upload Documents
          </SideNavLink>

          <SideNavLink
            renderIcon={Activity}
            as={NavLink}
            to="/jobs"
            className={styles.sideNavItem}
          >
            Job Monitor
          </SideNavLink>

          <SideNavLink
            renderIcon={Document}
            as={NavLink}
            to="/documents"
            className={styles.sideNavItem}
          >
            Documents
          </SideNavLink>
        </SideNavItems>
      </SideNav>
    </Theme>
  );
};

export default Navbar;

// Made with Bob
